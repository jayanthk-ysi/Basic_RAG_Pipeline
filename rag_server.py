import os
import re
import json
import time
import torch
import pickle
import uvicorn
import threading
from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_chroma import Chroma
from collections import defaultdict
from schemas import Analysis, Filters
from model_store import ensure_model
from sentence_transformers import CrossEncoder
from concurrent.futures import ThreadPoolExecutor
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from prompts import ANALYSIS_PROMPT, ANSWER_PROMPT, FILTER_PROMPT
from config import PROJECT_META, CLIENT_HINTS, DEV_ONLY, DOCS_DIR,CHROMA_PATH, CHUNKS_PATH, EMBEDDING_MODEL, RERANKER_MODEL, ROUTER_MODEL, ANSWER_MODEL, POOL_SIZE, RERANK_POOL, RRF_K, MIN_CANDIDATES, MIN_RELEVANCE, TOTAL_CHUNKS, MAX_PER_PROJECT, MAX_SUBQUERIES, MAX_HISTORY_TURNS, CLIENT_AUDIENCES, STATUS_IS_REAL, GREETING, OFF_TOPIC, OVERVIEW_PATH, RERANK_MAX_LENGTH, RERANK_BATCH_SIZE, USE_RERANKER, FILTERABLE_TAGS


load_dotenv() # loads GROQ_API_KEY from .env, must run before the ChatGroq clients are created below
import ragevalkit
torch.set_num_threads(os.cpu_count() or 4) # torch defaulted to 4 threads here; using all cores cut rerank time by about a third

embeddings = HuggingFaceEmbeddings(model_name=ensure_model(EMBEDDING_MODEL))
vectordb = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

with open(CHUNKS_PATH, "rb") as f:
    chunks = pickle.load(f)

reranker = CrossEncoder(ensure_model(RERANKER_MODEL), max_length=RERANK_MAX_LENGTH)
rerank_lock = threading.Lock()

router_llm = ChatGroq(model=ROUTER_MODEL, temperature=0)
answer_llm = ChatGroq(model=ANSWER_MODEL, temperature=0.4) # putting high as of now, since we require answer in non technical terms
# json_schema, because the default (tool calling) fails with openai/gpt-oss-20b on Groq
analysis_llm = router_llm.with_structured_output(Analysis, method="json_schema")
filters_llm = router_llm.with_structured_output(Filters, method="json_schema")

# shown when the customer says thanks / no thanks / a bare "yes" with nothing to search for, mid-conversation
CONTINUE = "Happy to help! Is there anything else you'd like to know about our projects, or something you'd like us to build?"

# shown instead of a server error when the answer model is unavailable (rate limit, outage); the turn is not saved to history
UNAVAILABLE = "Sorry, I'm having trouble answering right now. Please try again in a moment, or reach out to our team."

MAX_QUESTION_CHARS = 1000
JUNK_SUBQUERIES = {"technical", "relation", "kind", "sub_queries", "true", "false", "single", "independent", "connected",
                   "question", "greeting", "off_topic", "null", "none"}

ALL_TAGS = sorted({t for m in PROJECT_META.values() for t in m["tech_tags"].split(",") if t in FILTERABLE_TAGS})
DOMAINS = sorted({m["domain"] for m in PROJECT_META.values()})
PROJECT_LIST = "\n".join(f"- {stem}: {m['display_name']} ({m['project_category']})" for stem, m in PROJECT_META.items())


def retry_wait(error):
    # Groq rate-limit errors say "Please try again in 1.38s" (or "250ms"); otherwise wait a short fixed time
    m = re.search(r"try again in ([\d.]+)(ms|s)\b", error)
    if m:
        seconds = float(m.group(1)) / (1000 if m.group(2) == "ms" else 1)
        return min(seconds + 0.5, 10)
    return 1.0


def llm_call(runnable, prompt, retries=2):
    # Runs one LLM call and returns (result, stats). A fresh handler per call keeps token counts
    # separate for each stage, even when sub-queries run in parallel threads.
    # Retries cover the occasional unparseable structured output and Groq's tokens-per-minute limit.
    handler = UsageMetadataCallbackHandler()
    t = time.time()
    result, error, retried = None, None, 0

    for attempt in range(retries + 1):
        try:
            result = runnable.invoke(prompt, config={"callbacks": [handler]})
            error = None
            break
        except Exception as e:
            error = str(e)
            if attempt == retries or "401" in error or "invalid_api_key" in error.lower():
                break
            retried += 1
            time.sleep(retry_wait(error))

    usage = list(handler.usage_metadata.values())
    stats = {
        "seconds": round(time.time() - t, 2),
        "input_tokens": sum(u.get("input_tokens", 0) for u in usage),
        "output_tokens": sum(u.get("output_tokens", 0) for u in usage),
    }
    if retried:
        stats["retries"] = retried
    if error:
        stats["error"] = error

    return result, stats


def to_chroma_filter(specifications):
    filters = []

    for key, val in specifications.items():
        if isinstance(val,list):
            filters.append({key:{"$in":val}}) # if list, then match any one of it
        else:
            filters.append({key:{"$eq":val}}) # if a single value, then equals

    if not filters:
        return None

    if len(filters)==1:
        return filters[0]
    else:
        return {"$and": filters}


def matches(meta, spec):
    for key, val in spec.items():
        if isinstance(val, list):
            if meta.get(key) not in val:
                return False
        elif meta.get(key) != val:
            return False

    return True


# helper function for BM25
def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower()) # splits AB_CD --> AB, CD (easier for BM25 retrieval)


bm25_cache = {}
bm25_lock = threading.Lock() # due to multiple parallel calls


def get_bm25(specifications): # these are metadata filters
    key = json.dumps(specifications,sort_keys = True) # use the specification dictionary as a key & sorting makes it rearragement proof

    with bm25_lock:
        if key not in bm25_cache:
            subset = [c for c in chunks if matches(c.metadata,specifications)] # take only those specific chunks

            if subset:
                retriever = BM25Retriever.from_documents(subset, preprocess_func=tokenize)
                retriever.k = POOL_SIZE
                bm25_cache[key] = retriever

            else:
                bm25_cache[key] = None

        return bm25_cache[key]


get_bm25({})
get_bm25({"audience": CLIENT_AUDIENCES})

@ragevalkit.step("analysis")
def analyse(question, history):
    input_prompt = ANALYSIS_PROMPT.format(projects = PROJECT_LIST, history = history or "None", question = question, max_sub = MAX_SUBQUERIES)
    result, stats = llm_call(analysis_llm, input_prompt)

    if result is None:
        print("analysis failed, using the question as is:", stats.get("error"))
        return Analysis(kind = "question", technical = False, sub_queries = [question]), stats

    if result.kind == "question":
        subs = []
        for q in result.sub_queries:
            q = q.strip()
            words = re.findall(r"[A-Za-z']+", q)
            if len(words) < 2 or q.lower().strip(" :;,") in JUNK_SUBQUERIES: # after a retry the model sometimes leaks field names ("technical", ":false") into the list
                continue
            if q.lower() not in [s.lower() for s in subs]: # the model sometimes repeats a sub-query, which would search twice
                subs.append(q)

        if not subs: # nothing concrete to search for (e.g. a bare "yes" with no earlier offer), so don't search for the raw message
            return Analysis(kind="greeting"), stats

        if len(subs) > MAX_SUBQUERIES: # never drop a question: fold the extra ones into the last sub-query that is allowed
            subs = subs[:MAX_SUBQUERIES - 1] + [" ; ".join(subs[MAX_SUBQUERIES - 1:])]

        return Analysis(kind="question", relation=result.relation, technical=result.technical, sub_queries=subs), stats

    return result, stats


def extract_filters(sub_query, technical):
    spec = {} if technical else {"audience": list(CLIENT_AUDIENCES)}

    input_prompt = FILTER_PROMPT.format(projects=", ".join(PROJECT_META), domains=", ".join(DOMAINS), tags=", ".join(ALL_TAGS), question=sub_query)
    f, stats = llm_call(filters_llm, input_prompt)

    if f is None:
        print("filter extraction failed, using audience only:", stats.get("error"))
        return spec, stats

    if f.project in PROJECT_META:
        spec["project"] = f.project
    elif f.domain in DOMAINS:
        spec["domain"] = f.domain

    named = sub_query.lower().replace("-", " ").replace("_", " ")

    # a project written by its display name ("Healthcare Conversational AI Demo") is resolved here, because the model is only shown the short ids
    mentioned = [stem for stem, m in PROJECT_META.items() if m["display_name"].lower() in sub_query.lower()]
    if len(mentioned) == 1:
        spec["project"] = mentioned[0]
        spec.pop("domain", None)

    for tag in f.tech_tags:
        # only a real technology, and only if the customer actually wrote it (a wrong guess would hide other projects)
        if tag in ALL_TAGS and tag.replace("-", " ") in named:
            spec["tag_" + tag.replace("-", "_")] = True

    return spec, stats


# RETRIEVAL + RERANK

def rrf(result_lists):
    scores, docs = defaultdict(float), {}

    for results in result_lists:
        for rank, doc in enumerate(results):
            scores[doc.page_content] += 1.0 / (RRF_K + rank + 1)
            docs[doc.page_content] = doc

    best = sorted(scores, key=scores.get, reverse=True)[:RERANK_POOL]
    return [docs[c] for c in best]


def search_candidates(query, spec):
    # a domain is a hint, not a wall: also search without it, so a match from another domain (a pharmacy locator that lives in
    # an insurance project, for a question the model filed under healthcare) can still surface. Chunks in the hinted domain
    # appear in both searches, so they still rank higher.
    specs = [spec]
    if "domain" in spec and "project" not in spec:
        specs.append({k: v for k, v in spec.items() if k != "domain"})

    t_chroma = t_bm25 = 0.0
    result_lists = []
    for s in specs:
        t = time.time()
        chroma_docs = [d for d, _ in vectordb.similarity_search_with_score(query, k=POOL_SIZE, filter=to_chroma_filter(s))]
        t_chroma += time.time() - t

        t = time.time()
        bm25 = get_bm25(s)
        bm25_docs = bm25.invoke(query) if bm25 else []
        t_bm25 += time.time() - t

        result_lists += [chroma_docs, bm25_docs]

    t = time.time()
    fused = rrf(result_lists)
    t_rrf = time.time() - t

    return fused, {"chroma": t_chroma, "bm25": t_bm25, "rrf": t_rrf}

@ragevalkit.step("rerank")
def rerank(query, docs):
    if not docs:
        return []

    if not USE_RERANKER: # keep the hybrid (RRF) order
        return [(d, 0.0) for d in docs]

    with rerank_lock:
        scores = reranker.predict([(query, d.page_content) for d in docs], batch_size=RERANK_BATCH_SIZE)

    return sorted(zip(docs, map(float, scores)), key=lambda x: x[1], reverse=True)


def run_branch(sub_query, technical):
    base = {} if technical else {"audience": list(CLIENT_AUDIENCES)}
    spec, filter_stats = extract_filters(sub_query, technical)
    attempts = [spec] if spec == base else [spec, base]    # fall back to audience-only if filters find nothing good
    ranked = []

    stage_times = {"chroma": 0.0, "bm25": 0.0, "rrf": 0.0, "rerank": 0.0}
    rerank_pairs = 0
    final_spec, relaxed = attempts[-1], len(attempts) == 2

    for i, s in enumerate(attempts):
        candidates, times = search_candidates(sub_query, s)
        for name, seconds in times.items():
            stage_times[name] += seconds

        t = time.time()
        ranked = rerank(sub_query, candidates)
        stage_times["rerank"] += time.time() - t
        rerank_pairs += len(candidates)

        if len(candidates) >= MIN_CANDIDATES and ranked and (MIN_RELEVANCE is None or ranked[0][1] >= MIN_RELEVANCE):
            final_spec, relaxed = s, i == 1
            break

    stats = {"filters": filter_stats, "rerank_pairs": rerank_pairs, "attempts": i + 1}
    stats.update({f"{name}_s": round(seconds, 3) for name, seconds in stage_times.items()})

    return {"query": sub_query, "spec": final_spec, "relaxed": relaxed, "ranked": ranked, "stats": stats}


def combine(branches):
    quota = max(2, TOTAL_CHUNKS // len(branches))
    groups = []
    for b in branches:
        picked, per_project = [], defaultdict(int)
        capped = "project" not in b["spec"]
        for doc, score in b["ranked"]:
            if MIN_RELEVANCE is not None and score < MIN_RELEVANCE:
                break
            project = doc.metadata["project"]
            if capped and per_project[project] >= MAX_PER_PROJECT:
                continue
            picked.append((doc, score))
            per_project[project] += 1
            if len(picked) >= quota:
                break
        groups.append({"query": b["query"], "chunks": picked})
    return groups


overview = ""
with open(OVERVIEW_PATH,'r',encoding="utf-8") as f:
    overview = f.read()


def format_context(groups):
    parts = []

    # demo links come from PROJECT_META, so the model sees them whenever it mentions a project, whichever chunks were retrieved
    demos = {}
    for g in groups:
        for doc, _ in g["chunks"]:
            url = PROJECT_META[doc.metadata["project"]].get("demo_url")
            if url:
                demos[doc.metadata["display_name"]] = url
    if demos:
        parts.append("Demo links (only for the projects in this context):\n" + "\n".join(f"- {name}: {url}" for name, url in demos.items()))

    for i, g in enumerate(groups, 1):
        parts.append(f'=== Part {i}: "{g["query"]}" ===')
        if not g["chunks"]:
            parts.append("(No relevant information found for this part.)")
        for doc, _ in g["chunks"]:
            m = doc.metadata
            label = f"{m['display_name']} | {m['section']}"
            if STATUS_IS_REAL:
                label += f" | status: {m['status']} | timeline: {m['timeline']}"
            parts.append(f"[{label}]\n{doc.page_content}")
    return "\n\n".join(parts)


def overview_context():
    # for broad questions ("list your projects", "what do you do?"): no document excerpts, so the answer comes from the overview,
    # and every project's demo link is offered because the answer may mention any of them
    parts = ["(This is a broad question about our company and projects. There are no specific document excerpts for it: "
             "answer from the project overview above.)"]
    demos = {m["display_name"]: m["demo_url"] for m in PROJECT_META.values() if m.get("demo_url")}
    if demos:
        parts.append("Demo links:\n" + "\n".join(f"- {name}: {url}" for name, url in demos.items()))
    return "\n\n".join(parts)


def generate(question, history_text, groups, technical, overview_only=False):
    level = ("the customer asked for technical detail, so include technical specifics, still concisely"
             if technical else "plain, non-technical language, no jargon, explain terms in a few words")
    prompt = ANSWER_PROMPT.format(projects=overview, level=level, history=history_text or "(none)",
                                  context=overview_context() if overview_only else format_context(groups), question=question)

    result, stats = llm_call(answer_llm, prompt)
    if result is None:
        print("answer generation failed:", stats.get("error"))
        return None, stats

    return result.content, stats



histories = defaultdict(list) # session_id -> [(customer, assistant), ...]


def history_to_text(history):
    return "\n".join(f"Customer: {u}\nAssistant: {a}" for u, a in history[-MAX_HISTORY_TURNS:])


def handle(session_id, question):
    t0 = time.time()
    history = histories[session_id]
    history_text = history_to_text(history)
    failed = False

    question = question.strip()[:MAX_QUESTION_CHARS] # a pasted wall of text would cost thousands of tokens on every call
    if not question: # nothing to analyse, so no LLM call
        empty = {"seconds": 0.0, "input_tokens": 0, "output_tokens": 0}
        return {"answer": GREETING if not history else CONTINUE,
                "debug": {"kind": "greeting", "relation": "single", "technical": False, "sub_queries": []},
                "stats": {"analysis": empty, "branches": [], "total_s": 0.0, "tokens": {"llm_calls": 0, "input": 0, "output": 0, "total": 0}}}

    analysis, analysis_stats = analyse(question, history_text)

    ragevalkit.note("kind", analysis.kind)
    ragevalkit.note("technical", str(analysis.technical))
    ragevalkit.note("sub_queries", str(len(analysis.sub_queries)))

    stats = {"analysis": analysis_stats, "branches": []}

    debug = {"kind": analysis.kind, "relation": analysis.relation, "technical": analysis.technical, "sub_queries": analysis.sub_queries}

    if analysis.kind == "greeting":
        answer = GREETING if not history else CONTINUE
    elif analysis.kind == "off_topic":
        answer = OFF_TOPIC
    elif analysis.kind == "overview": # broad question: no sub-queries, no filter call, no search; answered from the overview
        with ragevalkit.step("generation"):
            answer, stats["generation"] = generate(question, history_text, [], analysis.technical, overview_only=True)
        if answer is None:
            answer, failed = UNAVAILABLE, True
    else:
        with ragevalkit.step("retrieval") as ret_step:
            t = time.time()
            with ThreadPoolExecutor(max_workers=len(analysis.sub_queries)) as pool:
                branches = list(pool.map(lambda q: run_branch(q, analysis.technical), analysis.sub_queries))
            stats["retrieval_wall_s"] = round(time.time() - t, 2) # sub-queries run in parallel, so this is not the sum

            t = time.time()
            groups = combine(branches)
            stats["combine_s"] = round(time.time() - t, 4)

            ret_step.material = format_context(groups)
            ret_step.sources = list({
                doc.metadata["project"]
                for g in groups
                for doc, _ in g["chunks"]
            })

        debug["branches"] = [{
            "query": b["query"], "filters": b["spec"], "relaxed": b["relaxed"],
            "top_scores": [round(s, 3) for _, s in b["ranked"][:5]],
        } for b in branches]
        debug["sources"] = [{"part": g["query"], "chunks": [
            {"project": d.metadata["project"], "section": d.metadata["section"], "score": round(s, 3)}
            for d, s in g["chunks"]]} for g in groups]
        stats["branches"] = [{"query": b["query"], **b["stats"]} for b in branches]

        # a short reply like "yes" means nothing to the answer step on its own, so tell it how the message was understood
        understood = " | ".join(analysis.sub_queries)
        asked = question if understood.strip().lower() == question.strip().lower() else f"{question}\n(Understood as: {understood})"

        with ragevalkit.step("generation"):
            answer, stats["generation"] = generate(asked, history_text, groups, analysis.technical)
        if answer is None:
            answer, failed = UNAVAILABLE, True

    if not failed: # a failed turn would leave the apology in the history and confuse the next question
        history.append((question, answer))
        if len(history) > MAX_HISTORY_TURNS * 3:
            del history[: len(history) - MAX_HISTORY_TURNS * 3]

    llm_calls = [stats["analysis"]] + [b["filters"] for b in stats["branches"]]
    if "generation" in stats:
        llm_calls.append(stats["generation"])

    stats["total_s"] = round(time.time() - t0, 2)
    stats["tokens"] = {
        "llm_calls": len(llm_calls),
        "input": sum(c["input_tokens"] for c in llm_calls),
        "output": sum(c["output_tokens"] for c in llm_calls),
    }
    stats["tokens"]["total"] = stats["tokens"]["input"] + stats["tokens"]["output"]

    return {"answer": answer, "debug": debug, "stats": stats}


# Use a dummy once, so the first query is faster
vectordb.similarity_search_with_score("warm up", k=1)
rerank("warm up", chunks[:2])



app = FastAPI()


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    return handle(req.session_id, req.message)


@app.post("/reset")
def reset(req: ChatRequest):
    histories.pop(req.session_id, None)
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ready", "chunks": len(chunks)}


if __name__ == "__main__":
    print("Ready. Server running on http://127.0.0.1:8000", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=8000)
