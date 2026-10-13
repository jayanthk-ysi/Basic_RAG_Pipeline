import re
import shutil
import pickle
from pathlib import Path
from langchain_chroma import Chroma
from langchain_core.documents import Document
from config import PROJECT_META, CLIENT_HINTS, DEV_ONLY, DOCS_DIR, EMBEDDING_MODEL, CHROMA_PATH, CHUNKS_PATH, OVERVIEW_PATH
from model_store import ensure_model
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter

dir_loader = DirectoryLoader(
    str(DOCS_DIR),
    loader_cls=TextLoader,
    loader_kwargs={"encoding":"utf-8"}
)

docs = dir_loader.load()

headers_to_split_on = [
    ('#',"Header 1"),
    ('##',"Header 2"),
    ('###',"Header 3")
]


def has(text, words):
    return any(re.search(rf"\b{re.escape(w)}", text) for w in words)


def classify(headers, default_audience="both"):
    # developer = only content a client would never need (setup, commands, env vars, file trees)
    # client    = overview / feature / workflow style sections
    # both      = everything else (shown to clients too)
    if not headers:
        return default_audience, "technical"

    leaf = headers[-1].lower()
    parent = headers[-2].lower() if len(headers) > 1 else ""

    if has(leaf, DEV_ONLY) or has(parent, DEV_ONLY):
        return "developer", "setup"
    if has(leaf, CLIENT_HINTS):
        return "client", "overview_or_feature"
    return default_audience, "technical"


# Chunking
markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on,strip_headers=False)

chunks = []
first_texts = {} # project -> text of its first section, used to write the project overview


def short_description(text, limit=420):
    # the first one or two plain paragraphs of a section: no headings, bold metadata lines, rules, code or bullet lists
    skip = ("#", "**Client", "**Demo", "**Type", "---", "```", "*", "-")
    kept = []
    for line in text.splitlines(): # the header splitter has already removed blank lines, so paragraphs are separate lines
        line = line.strip()
        if not line or line.startswith(skip):
            continue
        if line.endswith(":"): # a line ending in ":" only introduces a list that was dropped above
            continue
        kept.append(line)
        if sum(len(x) for x in kept) >= 200:
            break

    joined = " ".join(kept)
    if len(joined) <= limit:
        return joined
    cut = joined[:limit]
    return cut[: cut.rfind(". ") + 1] if ". " in cut else cut.rstrip() + "..."

for doc in docs:
    doc_content = doc.page_content
    doc_metadata = doc.metadata # Contains the source path
    # print("[doc_metadata]__ ",doc_metadata)

    md_split = markdown_splitter.split_text(doc_content)
    count = 0
    for md_doc in md_split:
        md_content = md_doc.page_content
        md_metadata = md_doc.metadata

        md_metadata.update(doc_metadata)

        # extracts file_name
        project_name = Path(md_metadata['source']).stem
        print("[project_name]__ ",project_name)

        if project_name not in PROJECT_META:
            raise KeyError(f"No PROJECT_META entry for '{project_name}'. Add it before indexing.")
        project_meta = PROJECT_META[project_name]

        # Adding a header in every document --> contains, project name and the section of its content
        formatted_header = f"Project: {project_name} \nSection: "

        if "Header 1" in md_metadata.keys():
            formatted_header+=f"{md_metadata['Header 1']}"

        if "Header 2" in md_metadata.keys():
            formatted_header+=f" -> {md_metadata['Header 2']}"

        if "Header 3" in md_metadata.keys():
            formatted_header+=f" -> {md_metadata['Header 3']}"

        formatted_header+="\n"

        # project-level fields (same for every chunk of the project) + chunk-level fields
        headers = [md_metadata[h] for h in ("Header 1", "Header 2", "Header 3") if h in md_metadata]
        section = " > ".join(headers)
        audience, section_type = classify(headers)

        md_metadata.update(project_meta)
        md_metadata.update({
            "project": project_name,
            "section": section,
            "audience": audience,
            "section_type": section_type,
        })
        # Chroma can't filter inside a string, so each tech tag becomes its own boolean field
        md_metadata.update({f"tag_{t.replace('-', '_')}": True for t in project_meta["tech_tags"].split(",")})

        final_content = formatted_header + md_content
        final_document = Document(page_content=final_content,metadata=md_metadata)

        chunks.append(final_document)

        if count==0:
            count=1
            first_texts[project_name] = md_content

# Check the labels before spending time on embeddings
for c in chunks:
    m = c.metadata
    print(f"{m['project']:<48} {m['audience']:<10} {m['section_type']:<20} {m['section']}")
print(f"\n{len(chunks)} chunks")

# Loading the embedding model
embedding_model = HuggingFaceEmbeddings(model_name=ensure_model(EMBEDDING_MODEL))

# Chroma appends to an existing index, so start from a clean one on every run
shutil.rmtree(CHROMA_PATH, ignore_errors=True)
vector_db = Chroma.from_documents(documents=chunks,embedding=embedding_model,persist_directory=CHROMA_PATH)


with open(OVERVIEW_PATH,'w',encoding="utf-8") as f:
    f.write("YoungSoft project overview (one entry per project):\n")
    for stem, meta in PROJECT_META.items():
        category = meta["project_category"].replace("e_prescribing", "e-prescribing").replace("_", " ")
        f.write(f"- {meta['display_name']} ({category}): {short_description(first_texts.get(stem, ''))}\n")

with open(CHUNKS_PATH,'wb') as f:
    pickle.dump(chunks,f)