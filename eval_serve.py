import ragevalkit
from rag_server import handle

def rag_fn(question: str, session_id: str = "") -> str:
    result = handle(session_id or "eval_default", question)
    return result["answer"]

ragevalkit.serve(
    rag_fn,
    port=8002,
    store_path="eval_store.json",
    judge_model="groq/openai/gpt-oss-20b",
    # judge_model="gemini/gemini-3.1-flash-lite-preview",
    session_params=["session_id"],
    session_id_fn=lambda chat_id: f"eval-{chat_id}",
    require_login=True,
    record_mode="eval",
    conversational_types=["overview"],
    record_detail="selected",
    answer_weight=0.6,
    material_weight=0.4,
    on_complete=lambda summary, rows: print(
        f"[eval] {summary['version']} done — "
        f"answer={summary.get('avg_answer_marks','?')}  "
        f"material={summary.get('avg_material_marks','?')}"
    ),
    users="jayanth:jayanth123",
)