import json
import math
import re
from collections import Counter
from typing import Any

from db.sqlite_db import get_connection

EMBED_DIM = 384

POSITIVE_WORDS = {
    "good", "great", "excellent", "approve", "approved", "resolved", "clear",
    "confident", "success", "improve", "done", "completed", "agree", "agreed",
}
NEGATIVE_WORDS = {
    "risk", "issue", "problem", "concern", "delay", "blocked", "blocker",
    "fail", "failed", "unclear", "conflict", "bug", "error", "debt",
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:['-][a-z0-9]+)?", text.lower())


def embed_text(text: str, dim: int = EMBED_DIM) -> list[float]:
    vec = [0.0] * dim
    tokens = _tokenize(text)
    if not tokens:
        return vec

    counts = Counter(tokens)
    for token, count in counts.items():
        idx = hash(token) % dim
        vec[idx] += float(count)

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


def split_into_chunks(text: str, chunk_size: int = 1400, overlap: int = 180) -> list[str]:
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks


def _speaker_sentiment_from_text(text: str) -> list[dict[str, Any]]:
    sentiments: list[dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        match = re.match(r"^\[\s*(.+?)\s*:\]\s*(.+)$", stripped)
        if not match:
            match = re.match(r"^([A-Za-z][A-Za-z0-9 .'\-&_]{1,80})\s*:\s*(.+)$", stripped)
        if not match:
            continue

        speaker = match.group(1).strip()
        utterance = match.group(2).strip()
        words = _tokenize(utterance)
        if not words:
            continue

        pos = sum(1 for w in words if w in POSITIVE_WORDS)
        neg = sum(1 for w in words if w in NEGATIVE_WORDS)
        score = (pos - neg) / max(1, len(words))
        label = "neutral"
        if score > 0.03:
            label = "positive"
        elif score < -0.03:
            label = "negative"

        sentiments.append(
            {
                "speaker": speaker,
                "sentiment_label": label,
                "sentiment_score": round(score, 4),
                "snippet": utterance[:240],
            }
        )
    return sentiments


def index_meeting(
    raw_text: str,
    file_name: str,
    analysis: dict[str, Any],
    stored_path: str,
) -> int:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO meetings (file_name, meeting_title, meeting_date, num_speakers, word_count, summary, stored_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_name,
            analysis.get("meeting_title", "Unknown"),
            analysis.get("meeting_date", "Unknown"),
            analysis.get("speaker_count", 0),
            analysis.get("word_count", 0),
            analysis.get("abstractive_summary", ""),
            stored_path,
        ),
    )
    meeting_id = int(cur.lastrowid)

    for idx, chunk in enumerate(split_into_chunks(raw_text)):
        emb = embed_text(chunk)
        cur.execute(
            """
            INSERT INTO transcript_chunks (meeting_id, chunk_index, chunk_text, chunk_embedding)
            VALUES (?, ?, ?, ?)
            """,
            (meeting_id, idx, chunk, json.dumps(emb)),
        )

    for decision in analysis.get("decisions", []):
        if isinstance(decision, str) and decision.strip():
            cur.execute(
                "INSERT INTO decisions (meeting_id, decision_text) VALUES (?, ?)",
                (meeting_id, decision.strip()),
            )

    for item in analysis.get("action_items", []):
        if not isinstance(item, dict):
            continue
        task = str(item.get("task", "")).strip()
        if not task:
            continue
        cur.execute(
            "INSERT INTO action_items (meeting_id, owner, task, due_by) VALUES (?, ?, ?, ?)",
            (
                meeting_id,
                str(item.get("owner", "Unknown")).strip() or "Unknown",
                task,
                str(item.get("due_by", "Unknown")).strip() or "Unknown",
            ),
        )

    for s in _speaker_sentiment_from_text(raw_text):
        cur.execute(
            """
            INSERT INTO transcript_sentiment (meeting_id, speaker, sentiment_label, sentiment_score, snippet)
            VALUES (?, ?, ?, ?, ?)
            """,
            (meeting_id, s["speaker"], s["sentiment_label"], s["sentiment_score"], s["snippet"]),
        )

    conn.commit()
    conn.close()
    return meeting_id


def search_chunks(question: str, limit: int = 6) -> list[dict[str, Any]]:
    q_emb = embed_text(question)
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT tc.meeting_id, tc.chunk_index, tc.chunk_text, tc.chunk_embedding, m.file_name, m.meeting_title, m.meeting_date
        FROM transcript_chunks tc
        JOIN meetings m ON m.id = tc.meeting_id
        """
    ).fetchall()
    conn.close()

    scored = []
    for row in rows:
        emb = json.loads(row["chunk_embedding"])
        score = cosine_similarity(q_emb, emb)
        scored.append(
            {
                "meeting_id": row["meeting_id"],
                "chunk_index": row["chunk_index"],
                "chunk_text": row["chunk_text"],
                "score": score,
                "file_name": row["file_name"],
                "meeting_title": row["meeting_title"],
                "meeting_date": row["meeting_date"],
            }
        )
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def fetch_sql_context(limit: int = 50) -> dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    decisions = cur.execute(
        """
        SELECT d.decision_text, m.file_name, m.meeting_title, m.meeting_date
        FROM decisions d JOIN meetings m ON m.id = d.meeting_id
        ORDER BY d.id DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    actions = cur.execute(
        """
        SELECT a.owner, a.task, a.due_by, m.file_name, m.meeting_title, m.meeting_date
        FROM action_items a JOIN meetings m ON m.id = a.meeting_id
        ORDER BY a.id DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    sentiments = cur.execute(
        """
        SELECT speaker, sentiment_label, sentiment_score, snippet, meeting_id
        FROM transcript_sentiment
        ORDER BY id DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    return {
        "decisions": [dict(r) for r in decisions],
        "action_items": [dict(r) for r in actions],
        "sentiments": [dict(r) for r in sentiments],
    }
