from __future__ import annotations

import sqlite3

from domain.evidence_extraction import (
    EvidenceExtraction,
    RiskOfBias,
)


DB_PATH = "evidence_extraction.db"


def initialize_database():

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS evidence_extractions (

            article_id TEXT PRIMARY KEY,

            doi TEXT,
            pmid TEXT,

            population TEXT,
            intervention TEXT,
            comparator TEXT,
            outcome TEXT,

            study_design TEXT,

            risk_of_bias TEXT,

            notes TEXT,

            updated_at TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def save_extraction(
    extraction: EvidenceExtraction,
):

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        INSERT OR REPLACE INTO
        evidence_extractions (

            article_id,

            doi,
            pmid,

            population,
            intervention,
            comparator,
            outcome,

            study_design,

            risk_of_bias,

            notes,

            updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            str(extraction.article_id),

            extraction.doi,
            extraction.pmid,

            extraction.population,
            extraction.intervention,
            extraction.comparator,
            extraction.outcome,

            extraction.study_design,

            extraction.risk_of_bias.value
            if extraction.risk_of_bias
            else None,

            extraction.notes,

            extraction.updated_at.isoformat(),
        ),
    )

    conn.commit()
    conn.close()


def load_extraction(
    article_id: str,
):

    conn = sqlite3.connect(DB_PATH)

    row = conn.execute(
        """
        SELECT

            doi,
            pmid,

            population,
            intervention,
            comparator,
            outcome,

            study_design,

            risk_of_bias,

            notes

        FROM evidence_extractions
        WHERE article_id = ?
        """,
        (article_id,),
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "doi": row[0],
        "pmid": row[1],
        "population": row[2],
        "intervention": row[3],
        "comparator": row[4],
        "outcome": row[5],
        "study_design": row[6],
        "risk_of_bias": row[7],
        "notes": row[8],
    }


def load_all_extractions():

    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute(
        """
        SELECT *
        FROM evidence_extractions
        """
    ).fetchall()

    conn.close()

    return rows
