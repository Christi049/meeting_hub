from fastapi import APIRouter
from db.sqlite_db import get_connection

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("")
def get_meetings():
    conn = get_connection()
    cur = conn.cursor()

    meetings = cur.execute("""
        SELECT id, file_name, meeting_title, meeting_date, num_speakers, word_count, summary, created_at
        FROM meetings
        ORDER BY created_at DESC
    """).fetchall()

    result = []
    for m in meetings:
        meeting_id = m["id"]

        decision_count = cur.execute(
            "SELECT COUNT(*) as c FROM decisions WHERE meeting_id = ?", (meeting_id,)
        ).fetchone()["c"]

        action_count = cur.execute(
            "SELECT COUNT(*) as c FROM action_items WHERE meeting_id = ?", (meeting_id,)
        ).fetchone()["c"]

        sentiment_row = cur.execute("""
            SELECT
                ROUND(AVG(sentiment_score), 3) as avg_score,
                SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as pos,
                SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as neg,
                SUM(CASE WHEN sentiment_label = 'neutral'  THEN 1 ELSE 0 END) as neu,
                COUNT(*) as total
            FROM transcript_sentiment
            WHERE meeting_id = ?
        """, (meeting_id,)).fetchone()

        overall_sentiment = "neutral"
        if sentiment_row and sentiment_row["total"] > 0:
            if sentiment_row["avg_score"] > 0.02:
                overall_sentiment = "positive"
            elif sentiment_row["avg_score"] < -0.02:
                overall_sentiment = "negative"

        result.append({
            "id": meeting_id,
            "file_name": m["file_name"],
            "title": m["meeting_title"] or m["file_name"],
            "date": m["meeting_date"],
            "num_speakers": m["num_speakers"],
            "word_count": m["word_count"],
            "summary": m["summary"],
            "created_at": m["created_at"],
            "decision_count": decision_count,
            "action_count": action_count,
            "overall_sentiment": overall_sentiment,
            "sentiment_score": sentiment_row["avg_score"] if sentiment_row else 0,
        })

    conn.close()
    return result