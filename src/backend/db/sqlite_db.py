import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "meetings.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            meeting_title TEXT,
            meeting_date TEXT,
            num_speakers INTEGER,
            word_count INTEGER,
            summary TEXT,
            stored_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transcript_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            chunk_embedding TEXT NOT NULL,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            decision_text TEXT NOT NULL,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS action_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            owner TEXT,
            task TEXT NOT NULL,
            due_by TEXT,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transcript_sentiment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            speaker TEXT,
            sentiment_label TEXT,
            sentiment_score REAL,
            snippet TEXT,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transcript_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            segment_index INTEGER NOT NULL,
            start_time TEXT,
            segment_text TEXT NOT NULL,
            sentiment_label TEXT,
            sentiment_score REAL,
            speaker_sentiments TEXT,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
        """
    )

    conn.commit()
    conn.close()


init_db()