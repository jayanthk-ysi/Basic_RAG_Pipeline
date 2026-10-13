import sys
import uuid

import requests

URL = "http://127.0.0.1:8000"
session_id = str(uuid.uuid4())
debug = "--debug" in sys.argv

def llm_label(label, call):
    return f'{label} [retried {call["retries"]}x]' if call.get("retries") else label


def row(label, seconds=None, tok_in=None, tok_out=None):
    secs = f"{seconds:>8.3f}" if seconds is not None else " " * 8
    t_in = f"{tok_in:>8}" if tok_in is not None else " " * 8
    t_out = f"{tok_out:>8}" if tok_out is not None else " " * 8
    print(f"  {label:<44}{secs}{t_in}{t_out}")


def print_stats(stats):
    print("\n  {:<44}{:>8}{:>8}{:>8}".format("stage", "sec", "tok in", "tok out"))
    print("  " + "-" * 68)

    a = stats["analysis"]
    row(llm_label("query analysis (LLM)", a), a["seconds"], a["input_tokens"], a["output_tokens"])

    for i, b in enumerate(stats["branches"], 1):
        print(f'  sub-query {i}: "{b["query"][:50]}"')
        f = b["filters"]
        row(llm_label("  metadata filter function (LLM)", f), f["seconds"], f["input_tokens"], f["output_tokens"])
        row("  chroma search", b["chroma_s"])
        row("  bm25 search", b["bm25_s"])
        row("  rrf fusion", b["rrf_s"])
        row(f'  rerank ({b["rerank_pairs"]} pairs, {b["attempts"]} attempt(s))', b["rerank_s"])

    if "retrieval_wall_s" in stats:
        row("retrieval, all sub-queries (parallel)", stats["retrieval_wall_s"])
        row("combine parts", stats["combine_s"])

    if "generation" in stats:
        g = stats["generation"]
        row(llm_label("answer generation (LLM)", g), g["seconds"], g["input_tokens"], g["output_tokens"])

    print("  " + "-" * 68)
    t = stats["tokens"]
    row(f'TOTAL ({t["llm_calls"]} LLM calls)', stats["total_s"], t["input"], t["output"])
    print(f'  total tokens: {t["total"]}')


print("YoungSoft assistant. Commands: /reset (new conversation), /debug (toggle details), /quit")

try:
    requests.get(f"{URL}/health", timeout=5)
except requests.exceptions.ConnectionError:
    sys.exit("Server not running. Start it first with:  python rag_server.py")

while True:
    question = input("\nYou: ").strip()
    if not question:
        continue
    if question == "/quit":
        break
    if question == "/reset":
        requests.post(f"{URL}/reset", json={"session_id": session_id, "message": ""})
        session_id = str(uuid.uuid4())
        print("Conversation cleared.")
        continue
    if question == "/debug":
        debug = not debug
        print("Debug", "on" if debug else "off")
        continue

    try:
        r = requests.post(f"{URL}/chat", json={"session_id": session_id, "message": question}, timeout=180)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        continue

    data = r.json()
    print("\nBot:", data["answer"])

    if debug:
        d = data["debug"]
        print("\n--- debug ---")
        print("kind:", d["kind"], "| relation:", d.get("relation", "-"), "| technical:", d["technical"])
        print("sub-queries:", d["sub_queries"])
        for b in d.get("branches", []):
            print(f'  "{b["query"]}"\n    filters: {b["filters"]} | relaxed: {b["relaxed"]} | top scores: {b["top_scores"]}')
        for s in d.get("sources", []):
            print(f'  sources for "{s["part"]}":')
            for c in s["chunks"]:
                print(f'    {c["score"]}  {c["project"]} > {c["section"]}')
        print_stats(data["stats"])