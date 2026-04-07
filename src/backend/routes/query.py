import json
import os
import re
from typing import Optional

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
    meeting_id: Optional[int] = None


# ── Intent classifier ──────────────────────────────────────────────────────────
# Returns a set of retrieval paths to activate: "vector", "sql", "sentiment"

INTENT_RULES = [
    # sentiment path
    (re.compile(
        r"\b(sentiment|tone|feel|stress|mood|positive|negative|tense|emotion|"
        r"happy|frustrated|confi(?:dent|dence)|enthus|concern(?:ed)?)\b",
        re.IGNORECASE,
    ), "sentiment"),
    # sql path — structured data
    (re.compile(
        r"\b(action item|action-item|task|to.?do|owner|due|deadline|assign|"
        r"decision|decided|agreed|conclusion|summary|summari[sz]e|list all|"
        r"all meeting|every meeting)\b",
        re.IGNORECASE,
    ), "sql"),
    # vector path — anything else narrative / semantic
    (re.compile(r".*", re.IGNORECASE), "vector"),
]


def classify_intent(question: str) -> set[str]:
    """Map question to one or more retrieval paths."""
    paths: set[str] = set()

    # Always add vector — it's the safe fallback for any narrative question
    paths.add("vector")

    for pattern, path in INTENT_RULES:
        if pattern.search(question):
            paths.add(path)

    # Explicit overrides: pure structured queries don't need vector
    if re.search(
        r"\b(list all|show all|all action items?|all decisions?)\b",
        question,
        re.IGNORECASE,
    ):
        paths.discard("vector")
        paths.add("sql")

    return paths


# ── Prompt templates ───────────────────────────────────────────────────────────

ROUTER_SYSTEM = """You are a meeting intelligence assistant with access to indexed meeting transcripts.
Answer the user's question using ONLY the provided context sections.

Context is labelled by source:
- [TRANSCRIPT CHUNKS] — verbatim excerpts ranked by relevance
- [DECISIONS] — structured decisions extracted from meetings
- [ACTION ITEMS] — tasks with owners and deadlines
- [SENTIMENT] — speaker tone analysis

Rules:
1. Ground every claim in the provided context. Do not invent facts.
2. If the context does not contain enough information, say so clearly.
3. For action items or decisions, list them concisely.
4. For sentiment queries, cite the speaker and their snippet.
5. Include 2-5 citations where possible.

You must respond with valid JSON only. No markdown, no code fences.
The JSON must have exactly two keys: answer (string) and citations (array of objects with keys meeting, section, quote)."""

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", ROUTER_SYSTEM),
    ("human", "Question: {question}\n\n{context}"),
])


# ── Context assemblers ─────────────────────────────────────────────────────────

def _build_vector_context(question: str, meeting_id: Optional[int]) -> str:
    chunks = search_chunks(question, limit=6, meeting_id=meeting_id)
    if not chunks:
        return ""
    lines = ["[TRANSCRIPT CHUNKS]"]
    for i, c in enumerate(chunks):
        lines.append(
            f"[{i+1}] {c['meeting_title']} ({c['meeting_date']}) · chunk {c['chunk_index']} · score {c['score']:.3f}\n"
            f"{c['chunk_text'][:800]}"
        )
    return "\n\n".join(lines)


def _build_sql_context(meeting_id: Optional[int]) -> str:
    data = fetch_sql_context(limit=40, meeting_id=meeting_id)
    parts = []

    if data["decisions"]:
        lines = ["[DECISIONS]"]
        for d in data["decisions"]:
            lines.append(f"• [{d['meeting_title']} · {d['meeting_date']}] {d['decision_text']}")
        parts.append("\n".join(lines))

    if data["action_items"]:
        lines = ["[ACTION ITEMS]"]
        for a in data["action_items"]:
            lines.append(
                f"• [{a['meeting_title']} · {a['meeting_date']}] "
                f"Owner: {a['owner']} | Task: {a['task']} | Due: {a['due_by']}"
            )
        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def _build_sentiment_context(meeting_id: Optional[int]) -> str:
    data = fetch_sql_context(limit=40, meeting_id=meeting_id)
    if not data["sentiments"]:
        return ""
    lines = ["[SENTIMENT]"]
    for s in data["sentiments"]:
        lines.append(
            f"• Speaker: {s['speaker']} | {s['sentiment_label']} (score {s['sentiment_score']:.3f})\n"
            f"  \"{s['snippet'][:200]}\""
        )
    return "\n".join(lines)


def _deterministic_fallback(question: str, meeting_id: Optional[int]) -> dict:
    """Used when no LLM API key is configured."""
    chunks = search_chunks(question, limit=3, meeting_id=meeting_id)
    if not chunks:
        return {
            "answer": "No indexed transcripts found yet. Please upload a transcript file first.",
            "citations": [],
        }
    answer = "Based on indexed transcripts:\n\n" + "\n\n".join(
        f"**{c['meeting_title']} ({c['meeting_date']}):**\n{c['chunk_text'][:300]}..."
        for c in chunks
    )
    citations = [
        {
            "meeting": c["meeting_title"],
            "section": f"chunk {c['chunk_index']}",
            "quote": c["chunk_text"][:200],
        }
        for c in chunks
    ]
    return {"answer": answer, "citations": citations}


# ── Route handler ──────────────────────────────────────────────────────────────

@router.post("")
def ask_query(payload: QueryRequest):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    if not llm:
        return _deterministic_fallback(question, payload.meeting_id)

    # 1. Classify intent → decide which retrieval paths to activate
    paths = classify_intent(question)

    # 2. Fetch context from each active path
    context_blocks: list[str] = []

    if "vector" in paths:
        block = _build_vector_context(question, payload.meeting_id)
        if block:
            context_blocks.append(block)

    if "sql" in paths:
        block = _build_sql_context(payload.meeting_id)
        if block:
            context_blocks.append(block)

    if "sentiment" in paths:
        block = _build_sentiment_context(payload.meeting_id)
        if block:
            context_blocks.append(block)

    if not context_blocks:
        return {
            "answer": "No relevant information found in the uploaded transcripts for that question.",
            "citations": [],
        }

    context = "\n\n---\n\n".join(context_blocks)

    # 3. Call LLM with structured context
    try:
        chain = ANSWER_PROMPT | llm
        resp = chain.invoke({"question": question, "context": context})
        raw = resp.content.strip()
        if raw.startswith("```"):
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"answer": resp.content.strip(), "citations": []}
    except Exception as e:
        return {
            "answer": f"Error generating answer: {str(e)}",
            "citations": [],
        }

    if "answer" not in parsed:
        parsed["answer"] = "Could not produce a grounded answer."
    if not isinstance(parsed.get("citations"), list):
        parsed["citations"] = []

    return parsed