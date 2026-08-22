import sqlite3

DB_PATH = "screening.db"


def initialize_database():
    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS screening_decisions (
            article_key TEXT PRIMARY KEY,
            decision TEXT,
            reason TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def save_decision(
    article_key: str,
    decision: str,
    reason: str | None,
):
    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        INSERT OR REPLACE INTO screening_decisions
        (
            article_key,
            decision,
            reason
        )
        VALUES (?, ?, ?)
        """,
        (
            article_key,
            decision,
            reason,
        ),
    )

    conn.commit()
    conn.close()


def load_decisions():
    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute(
        """
        SELECT
            article_key,
            decision,
            reason
        FROM screening_decisions
        """
    ).fetchall()

    conn.close()

    return {
        row[0]: {
            "decision": row[1],
            "reason": row[2],
        }
        for row in rows
    }
