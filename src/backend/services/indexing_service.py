import json
import math
import re
from collections import Counter
from typing import Any, Optional

from db.sqlite_db import get_connection

EMBED_DIM = 384

POSITIVE_WORDS = {
    # Leadership & Achievement
    "good", "great", "excellent", "outstanding", "fantastic", "wonderful", "amazing",
    "approve", "approved", "approval", "resolved", "clear", "clarity", "confident",
    "success", "successful", "succeed", "improve", "improvement", "improved", "done",
    "completed", "complete", "agree", "agreed", "agreement", "alignment", "aligned",
    "progress", "progressing", "achieved", "achievement", "accomplish", "accomplished",
    
    # Positive Emotions & Attitudes
    "love", "loved", "enjoy", "enjoyed", "enjoy", "pleasure", "happy", "happily",
    "excited", "exciting", "enthusiasm", "enthusiastic", "eager", "wonderful", "great",
    "kudos", "praise", "praised", "appreciate", "appreciated", "appreciation", "grateful",
    "thanks", "thank", "thankyou", "brilliant", "awesome", "fantastic", "incredible",
    
    # Solutions & Efficiency
    "solution", "solved", "fix", "fixed", "working", "works", "smooth", "smoothly",
    "efficient", "efficient", "quickly", "fast", "rapid", "improvement", "optimize",
    "optimized", "streamline", "streamlined", "enhance", "enhanced", "boost", "boost",
    
    # Team & Collaboration
    "team", "teamwork", "collaborative", "collaborate", "together", "partner", "partnership",
    "support", "supported", "helping", "help", "cooperate", "cooperation", "unity",
    
    # Business Positive
    "revenue", "profit", "profitable", "growth", "grow", "increase", "increased",
    "opportunity", "opportunities", "potential", "promise", "promising", "guarantee",
}

NEGATIVE_WORDS = {
    # Problems & Issues
    "risk", "risks", "risky", "issue", "issues", "problem", "problems", "concern",
    "concerns", "concerned", "delay", "delayed", "delays", "blocked", "blocker",
    "blockers", "fail", "failed", "failure", "unclear", "unclear", "confusion",
    "conflict", "conflicts", "conflicting", "bug", "bugs", "error", "errors",
    "debt", "technical_debt",
    
    # Negative Emotions & Attitudes
    "bad", "terrible", "horrible", "awful", "hate", "hated", "dislike", "disliked",
    "angry", "anger", "frustrated", "frustration", "disappointed", "disappointing",
    "upset", "concern", "worried", "worry", "anxious", "anxiety", "panic", "stressed",
    "stress", "sad", "sadness", "unhappy", "miserable", "dread", "fear", "feared",
    
    # Inefficiency & Barriers
    "slow", "slower", "slowdown", "stuck", "stalled", "deadlock", "inefficient",
    "inefficiency", "wasteful", "waste", "redundant", "duplicate", "fragmented",
    "fragmentation", "inconsistent", "complexity", "complicated", "confusing",
    
    # Negative Business Terms
    "loss", "losses", "decline", "declining", "decreased", "decrease", "drop",
    "dropped", "falling", "fall", "crash", "crashed", "outage", "down", "shutdown",
    "discontinued", "abandoned", "incomplete", "unfinished", "partial",
    
    # Critical Issues
    "critical", "critical", "severe", "serious", "dangerous", "hazard", "vulnerability",
    "security", "breach", "compromised", "broken", "corrupt", "corrupted",
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
        total_words = len(words)
        
        # Calculate sentiment score: (positive - negative) / total
        # This gives a value between -1 and 1
        score = (pos - neg) / total_words if total_words > 0 else 0
        
        # Classify based on the score with reasonable thresholds
        # Threshold of ±0.05 means at least 5% net sentiment for classification
        # E.g., in a 100-word utterance: 5+ pos vs 0 neg is positive
        label = "neutral"
        if score > 0.05:
            label = "positive"
        elif score < -0.05:
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


def _compute_segment_sentiments(text: str, words_per_segment: int = 2250) -> list[dict[str, Any]]:
    """
    Split transcript into 5-minute segments and compute sentiment for each.
    Estimates ~450 words/minute, so ~2250 words per 5-minute segment.
    Returns list of segments with overall sentiment and per-speaker breakdown.
    """
    if not text.strip():
        return []

    segments = []
    words_list = _tokenize(text)
    if not words_list:
        return []

    total_words = len(words_list)
    num_segments = max(1, (total_words + words_per_segment - 1) // words_per_segment)
    words_per_actual_segment = max(1, total_words // num_segments)

    # Split by approximate word count
    current_pos = 0
    segment_idx = 0

    for segment_idx in range(num_segments):
        # Find segment boundaries in characters (approximate)
        start_word_idx = segment_idx * words_per_actual_segment
        end_word_idx = min((segment_idx + 1) * words_per_actual_segment, total_words)

        # Reconstruct character positions (simplified approach)
        chars_per_word_avg = len(text) / max(1, total_words)
        char_start = int(start_word_idx * chars_per_word_avg)
        char_end = int(end_word_idx * chars_per_word_avg)

        # Refine boundaries to word/line breaks for readability
        char_start = max(0, text.rfind(" ", 0, char_start) + 1)
        char_end = min(len(text), text.find(" ", char_end) + 1)

        segment_text = text[char_start:char_end].strip()
        if not segment_text:
            continue

        # Compute segment-level sentiment
        speaker_sentiments = _speaker_sentiment_from_text(segment_text)

        if speaker_sentiments:
            # Aggregate sentiment across speakers in segment
            scores = [s["sentiment_score"] for s in speaker_sentiments]
            avg_score = sum(scores) / len(scores)
            label = "neutral"
            if avg_score > 0.05:
                label = "positive"
            elif avg_score < -0.05:
                label = "negative"
        else:
            # No speaker data, use simple word list approach
            seg_words = _tokenize(segment_text)
            pos = sum(1 for w in seg_words if w in POSITIVE_WORDS)
            neg = sum(1 for w in seg_words if w in NEGATIVE_WORDS)
            total_words = len(seg_words)
            avg_score = (pos - neg) / total_words if total_words > 0 else 0
            label = "neutral"
            if avg_score > 0.05:
                label = "positive"
            elif avg_score < -0.05:
                label = "negative"
            speaker_sentiments = []

        # Calculate time range based on word position
        start_minutes = int(start_word_idx / 450)  # ~450 words/min
        end_minutes = int(end_word_idx / 450)
        start_time = f"{start_minutes}:00"
        end_time = f"{end_minutes}:00"

        segments.append({
            "segment_index": len(segments),
            "start_time": f"{start_time}-{end_time}",
            "segment_text": segment_text,
            "sentiment_label": label,
            "sentiment_score": round(avg_score, 4),
            "speaker_sentiments": speaker_sentiments,
        })

    return segments


def index_meeting(
    raw_text: str,
    file_name: str,
    analysis: dict[str, Any],
    stored_path: str,
) -> tuple[int, list[dict[str, Any]]]:
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

    # Compute and store segment-level sentiments
    segments = _compute_segment_sentiments(raw_text)
    for segment in segments:
        cur.execute(
            """
            INSERT INTO transcript_segments (meeting_id, segment_index, start_time, segment_text, sentiment_label, sentiment_score, speaker_sentiments)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                meeting_id,
                segment["segment_index"],
                segment["start_time"],
                segment["segment_text"],
                segment["sentiment_label"],
                segment["sentiment_score"],
                json.dumps(segment["speaker_sentiments"]),
            ),
        )

    conn.commit()
    conn.close()
    return meeting_id, segments


def search_chunks(question: str, limit: int = 6, meeting_id: Optional[int] = None) -> list[dict[str, Any]]:
    q_emb = embed_text(question)
    conn = get_connection()
    cur = conn.cursor()
    
    query = """
        SELECT tc.meeting_id, tc.chunk_index, tc.chunk_text, tc.chunk_embedding, m.file_name, m.meeting_title, m.meeting_date
        FROM transcript_chunks tc
        JOIN meetings m ON m.id = tc.meeting_id
    """
    params: tuple[Any, ...] = ()
    
    if meeting_id is not None:
        query += " WHERE tc.meeting_id = ?"
        params = (meeting_id,)
    
    rows = cur.execute(query, params).fetchall()
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


def fetch_sql_context(limit: int = 50, meeting_id: Optional[int] = None) -> dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    
    # Build queries with optional meeting_id filter
    decision_query = """
        SELECT d.decision_text, m.file_name, m.meeting_title, m.meeting_date
        FROM decisions d JOIN meetings m ON m.id = d.meeting_id
    """
    action_query = """
        SELECT a.owner, a.task, a.due_by, m.file_name, m.meeting_title, m.meeting_date
        FROM action_items a JOIN meetings m ON m.id = a.meeting_id
    """
    sentiment_query = """
        SELECT speaker, sentiment_label, sentiment_score, snippet, meeting_id
        FROM transcript_sentiment
    """
    
    if meeting_id is not None:
        decision_query += " WHERE d.meeting_id = ?"
        action_query += " WHERE a.meeting_id = ?"
        sentiment_query += " WHERE meeting_id = ?"
        query_params = (meeting_id,)
    else:
        query_params = ()
    
    decision_query += " ORDER BY d.id DESC LIMIT ?"
    action_query += " ORDER BY a.id DESC LIMIT ?"
    sentiment_query += " ORDER BY id DESC LIMIT ?"
    
    decisions = cur.execute(decision_query, (*query_params, limit)).fetchall()
    actions = cur.execute(action_query, (*query_params, limit)).fetchall()
    sentiments = cur.execute(sentiment_query, (*query_params, limit)).fetchall()
    
    conn.close()

    return {
        "decisions": [dict(r) for r in decisions],
        "action_items": [dict(r) for r in actions],
        "sentiments": [dict(r) for r in sentiments],
    }
