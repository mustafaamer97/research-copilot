from uuid import uuid4

from domain.evidence_extraction import (
    EvidenceExtraction,
    RiskOfBias,
)

from infrastructure.sqlite_extraction import (
    initialize_database,
    save_extraction,
    load_extraction,
)


def test_save_and_load_extraction():

    initialize_database()

    article_id = uuid4()

    extraction = EvidenceExtraction(
        article_id=article_id,
        population="Adults",
        intervention="ACE inhibitor",
        comparator="Placebo",
        outcome="Blood pressure reduction",
        study_design="RCT",
        risk_of_bias=RiskOfBias.LOW,
        notes="Test note",
    )

    save_extraction(extraction)

    loaded = load_extraction(
        str(article_id)
    )

    assert loaded is not None

    assert loaded["population"] == "Adults"

    assert (
        loaded["intervention"]
        == "ACE inhibitor"
    )

    assert (
        loaded["comparator"]
        == "Placebo"
    )

    assert (
        loaded["outcome"]
        == "Blood pressure reduction"
    )

    assert (
        loaded["study_design"]
        == "RCT"
    )

    assert (
        loaded["risk_of_bias"]
        == "Low"
    )

    assert (
        loaded["notes"]
        == "Test note"
    )


def test_overwrite_existing_extraction():

    initialize_database()

    article_id = uuid4()

    first = EvidenceExtraction(
        article_id=article_id,
        population="Adults",
        risk_of_bias=RiskOfBias.LOW,
    )

    save_extraction(first)

    second = EvidenceExtraction(
        article_id=article_id,
        population="Children",
        risk_of_bias=RiskOfBias.HIGH,
    )

    save_extraction(second)

    loaded = load_extraction(
        str(article_id)
    )

    assert loaded["population"] == "Children"

    assert (
        loaded["risk_of_bias"]
        == "High"
    )
