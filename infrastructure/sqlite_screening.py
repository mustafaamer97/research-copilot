import sqlite3


DB_PATH = "screening.db"


def initialize_database():

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS screening_decisions (

            article_key TEXT PRIMARY KEY,

            title TEXT,
            abstract TEXT,

            authors TEXT,
            journal TEXT,
            publication_date TEXT,

            doi TEXT,
            pmid TEXT,

            source TEXT,
            url TEXT,

            decision TEXT,
            reason TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def save_decision(
    article_key,
    article,
    decision,
    reason,
):

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        INSERT OR REPLACE INTO screening_decisions (

            article_key,

            title,
            abstract,

            authors,
            journal,
            publication_date,

            doi,
            pmid,

            source,
            url,

            decision,
            reason

        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            article_key,

            article.title,
            article.abstract,

            "; ".join(article.authors),

            article.journal,
            article.publication_date,

            article.doi,
            article.pmid,

            article.source.value,
            article.url,

            decision,
            reason,
        ),
    )

    conn.commit()
    conn.close()
