import json
import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from services.indexing_service import fetch_sql_context, search_chunks

router = APIRouter(prefix="/query", tags=["query"])

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path)
api_key = os.getenv("OPENROUTER_API_KEY")
llm = None
if api_key:
    llm = ChatOpenAI(
        model="openai/gpt-4o-mini",
        temperature=0.1,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
    )


class QueryRequest(BaseModel):
    question: str


ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a meeting intelligence assistant.
Answer user questions using the provided retrieval context.
Return ONLY valid JSON with:
{
  "answer": "concise answer",
  "citations": [{"meeting":"...", "section":"chunk N", "quote":"..."}]
}

Rules:
- Base answer only on provided context.
- Include 2-5 citations where possible.
- If evidence is weak, say so explicitly.
""",
        ),
        (
            "human",
            "Question:\n{question}\n\nTop chunks:\n{chunks}\n\nSQL context:\n{sql_context}",
        ),
    ]
)


@router.post("")
def ask_query(payload: QueryRequest):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    top_chunks = search_chunks(question, limit=8)
    sql_context = fetch_sql_context(limit=60)

    if not llm:
        # Deterministic fallback when API key is unavailable.
        if not top_chunks:
            return {"answer": "No indexed transcripts found yet.", "citations": []}
        best = top_chunks[:3]
        answer = "Based on indexed transcripts, the closest discussions are:\n" + "\n".join(
            f"- {c['meeting_title']} ({c['meeting_date']}): {c['chunk_text'][:180]}..."
            for c in best
        )
        citations = [
            {
                "meeting": f"{c['meeting_title']} ({c['meeting_date']})",
                "section": f"chunk {c['chunk_index']}",
                "quote": c["chunk_text"][:220],
            }
            for c in best
        ]
        return {"answer": answer, "citations": citations}

    chunk_blob = "\n\n".join(
        f"[{i+1}] Meeting={c['meeting_title']} Date={c['meeting_date']} File={c['file_name']} chunk={c['chunk_index']}\n{c['chunk_text'][:1000]}"
        for i, c in enumerate(top_chunks)
    )
    sql_blob = json.dumps(sql_context, ensure_ascii=True)[:12000]
    chain = ANSWER_PROMPT | llm
    resp = chain.invoke({"question": question, "chunks": chunk_blob, "sql_context": sql_blob})
    raw = resp.content.strip()
    if raw.startswith("```"):
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {"answer": raw, "citations": []}
    if "answer" not in parsed:
        parsed["answer"] = "I could not produce a grounded answer."
    if "citations" not in parsed or not isinstance(parsed["citations"], list):
        parsed["citations"] = []
    return parsed
