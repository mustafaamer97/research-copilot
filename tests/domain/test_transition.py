"""Tests for TransitionRecord."""
import pytest
from uuid import uuid4
from domain.actors import ActorType
from domain.state import ResearchState
from domain.transition import TransitionRecord


def _make_record(**kwargs):
    defaults = dict(
        project_id=uuid4(),
        from_state=ResearchState.IDEA,
        to_state=ResearchState.QUESTION_DEFINED,
        actor=ActorType.RESEARCHER,
        reason="Researcher confirmed question.",
    )
    defaults.update(kwargs)
    return TransitionRecord(**defaults)


def test_valid_transition_record_accepted():
    rec = _make_record()
    assert rec.from_state == ResearchState.IDEA
    assert rec.to_state == ResearchState.QUESTION_DEFINED
    assert rec.actor == ActorType.RESEARCHER


def test_transition_record_has_id_and_timestamp():
    rec = _make_record()
    assert rec.id is not None
    assert rec.timestamp is not None


def test_transition_record_is_immutable():
    rec = _make_record()
    with pytest.raises(Exception):
        rec.reason = "Mutated"


def test_transition_record_frozen_from_state():
    rec = _make_record()
    with pytest.raises(Exception):
        rec.from_state = ResearchState.FRAMEWORK_DEFINED


def test_transition_uses_research_state():
    rec = _make_record(
        from_state=ResearchState.FRAMEWORK_DEFINED,
        to_state=ResearchState.DESIGN_SELECTED,
    )
    assert isinstance(rec.from_state, ResearchState)
    assert isinstance(rec.to_state, ResearchState)


def test_transition_uses_actor_type():
    for actor in ActorType:
        rec = _make_record(actor=actor)
        assert rec.actor == actor
