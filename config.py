from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "documents"

PROJECT_META = {
    "scriber_agent": {
        "display_name": "Scriber Agent",
        "domain": "healthcare",
        "project_category": "clinical_documentation",
        "audience": "both",
        "tech_tags": "python,fastapi,uvicorn,celery,redis,postgresql,mongodb,"
                     "langchain,langgraph,deepgram,gemini,groq,websocket,"
                     "chrome-extension,react,vite",
        "status": "pilot",
        "timeline": "2025-Q2 to 2025-Q4",
        "completed_year": 2025,
    },
    "ai_listener": {
        "display_name": "Healthcare Conversational AI Demo",
        "domain": "healthcare",
        "project_category": "conversational_ai",
        "audience": "both",
        "tech_tags": "python,fastapi,groq,pydantic,javascript,html-css",
        "status": "poc",
        "timeline": "2025-Q1 to 2025-Q2",
        "completed_year": 2025,
    },
    "retell_caller_agent": {
        "display_name": "AI Physiotherapy Call Agent",
        "domain": "healthcare",
        "project_category": "voice_agent",
        "audience": "both",
        "tech_tags": "python,fastapi,retell-ai,telnyx,javascript,json",
        "status": "poc",
        "timeline": "2025-Q2 to 2025-Q3",
        "completed_year": 2025,
    },
    "digital-prescription-virtual-assistant-platform": {
        "display_name": "Digital Prescription & Virtual Assistant Platform",
        "demo_url": "https://h2hsolutions.com/drx-virtual-assitance/",
        "domain": "healthcare",
        "project_category": "e_prescribing",
        "audience": "both",
        "tech_tags": "e-prescribing,predictive-analytics,ai-assistant,"
                     "prior-authorization,clinical-decision-support",
        "status": "live",
        "timeline": "2024-Q3 to 2025-Q1",
        "completed_year": 2025,
    },
    "intelligent-reporting-system": {
        "display_name": "Intelligent Reporting System",
        "demo_url": "https://ailabs.youngsoft.com/reports/login",
        "domain": "healthcare",
        "project_category": "reporting_analytics",
        "audience": "both",
        "tech_tags": "conversational-search,crm-integration,dashboard,"
                     "knowledge-search,ai",
        "status": "live",
        "timeline": "2024-Q4 to 2025-Q2",
        "completed_year": 2025,
    },
    "siho_rag": {
        "display_name": "MyTruAdvantage (MTA) Health Plan Chatbot",
        "demo_url": "https://dev.mytruadvantage.com",
        "domain": "insurance",
        "project_category": "chatbot",
        "audience": "both",
        "tech_tags": "chatbot,rag,bilingual,english,spanish,human-handoff",
        "status": "live",
        "timeline": "2024-Q2 to 2024-Q4",
        "completed_year": 2024,
    },
    "ysi_ras": {
        "display_name": "YSIRas Recruitment Assessment System",
        "demo_url": "https://recruitment.youngsoft.in",
        "domain": "hr",
        "project_category": "recruitment",
        "audience": "both",
        "tech_tags": "resume-screening,video-interview,ats-integration,"
                     "candidate-evaluation,dashboard,ai",
        "status": "live",
        "timeline": "2024-Q1 to 2024-Q3",
        "completed_year": 2024,
    },
}

DEV_ONLY = ("setup", "install", "installation", "environment", "configuration", "running the",
            "run the", "quick start", "api reference", "api endpoints", "endpoints",
            "folder structure", "project structure", "license", "standalone", "grant microphone",
            "load the extension", "enable developer", "open chrome", "generate the extension")


CLIENT_HINTS = ("overview", "feature", "highlight", "business value", "capabilit", "workflow",
                "flow", "summaries", "pages", "page", "dashboard", "how it works", "client", "demo")

# Only real technologies can be used as a search filter. The other tech_tags (chatbot, dashboard, ai, bilingual, ...) describe
# features, and filtering on them hid relevant projects (a "chatbot" question was narrowed to a single project).
FILTERABLE_TAGS = ("python", "fastapi", "uvicorn", "celery", "redis", "postgresql", "mongodb", "langchain", "langgraph",
                   "deepgram", "gemini", "groq", "websocket", "chrome-extension", "react", "vite", "pydantic",
                   "javascript", "html-css", "retell-ai", "telnyx", "json")



CHROMA_PATH = str(BASE_DIR / "chroma")
CHUNKS_PATH = str(BASE_DIR / "chunks.pkl")
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
# measured on this machine for ~25 chunks: MiniLM ~1s, bge-reranker-base ~6s, with no retrieval gain on the 34 eval questions
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2" # slower option: "BAAI/bge-reranker-base"
RERANK_MAX_LENGTH = 256    # tokens per (question, chunk) pair; chunks are short, and this roughly halves the time
RERANK_BATCH_SIZE = 16
USE_RERANKER = True        # False = keep the hybrid (RRF) order and skip the reranker entirely. Measured on 34 questions, answer chunk in
                           # top 3: hybrid 26, MiniLM 28 (top 6: 30 vs 31). Mixed per question, so it is a small net gain, not a sure one
ROUTER_MODEL = "openai/gpt-oss-20b"             # sub-queries + filters 
ANSWER_MODEL = "openai/gpt-oss-20b"

POOL_SIZE = 20             # results taken from each retriever
RERANK_POOL = 25           # fused candidates sent to the reranker
RRF_K = 60
MIN_CANDIDATES = 1         # retry with the audience-only filter only when the filters match nothing. Filters keep or drop whole projects, so a
                           # wrong guess gives 0 hits. A threshold of 5 wrongly dropped the project filter for small projects (the call agent has 4 client chunks)
MIN_RELEVANCE = None       # None = never drop chunks by reranker score. Measured: raw scores can't separate answerable client
                           # questions from off-topic ones (both land at the bottom), so a cutoff would hide good answers
TOTAL_CHUNKS = 8           # chunks sent to the answer LLM across all sub-queries (split evenly: 2 parts = 4 each, 3 parts = 2 each)
MAX_PER_PROJECT = 3        # diversity cap (not applied when a project was named)
MAX_SUBQUERIES = 3
MAX_HISTORY_TURNS = 6

CLIENT_AUDIENCES = ["client", "both"]
STATUS_IS_REAL = False     # since it's dummy values, currently put it as False

GREETING = ("Hi! I can tell you about the software projects we've built, such as healthcare assistants, "
            "reporting tools and recruitment platforms, and how we could help with yours. What are you looking for?")

OFF_TOPIC = ("I can only help with questions about our projects and services. "
             "Tell me what you'd like to achieve and I'll show you the closest thing we've built.")

OVERVIEW_PATH = str(BASE_DIR / "overview.txt")