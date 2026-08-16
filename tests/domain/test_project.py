"""Tests for ResearchProject aggregate root."""
import pytest
from domain.project import ResearchProject
from domain.state import ResearchState
from domain.framework import ResearchFramework, FrameworkType


def _make_project(**kwargs):
    defaults = dict(title="Test Project", idea="An interesting research idea.")
    defaults.update(kwargs)
    return ResearchProject(**defaults)


def test_new_project_starts_at_idea():
    p = _make_project()
    assert p.state == ResearchState.IDEA


def test_project_state_is_research_state():
    p = _make_project()
    assert isinstance(p.state, ResearchState)


def test_project_has_id():
    p = _make_project()
    assert p.id is not None


def test_project_title_stored():
    p = _make_project(title="My Study")
    assert p.title == "My Study"


def test_project_idea_stored():
    p = _make_project(idea="Explore cardiovascular outcomes.")
    assert p.idea == "Explore cardiovascular outcomes."


def test_empty_title_rejected():
    with pytest.raises(Exception):
        _make_project(title="")


def test_whitespace_title_rejected():
    with pytest.raises(Exception):
        _make_project(title="   ")


def test_empty_idea_rejected():
    with pytest.raises(Exception):
        _make_project(idea="")


def test_whitespace_idea_rejected():
    with pytest.raises(Exception):
        _make_project(idea="   ")


def test_research_question_defaults_none():
    p = _make_project()
    assert p.research_question is None


def test_framework_defaults_none():
    p = _make_project()
    assert p.framework is None


def test_tasks_default_empty_list():
    p = _make_project()
    assert p.tasks == []


def test_transition_history_defaults_empty_list():
    p = _make_project()
    assert p.transition_history == []


def test_tasks_are_independent_between_instances():
    p1 = _make_project()
    p2 = _make_project()
    p1.tasks.append("x")  # type: ignore
    assert p2.tasks == []


def test_transition_history_independent_between_instances():
    p1 = _make_project()
    p2 = _make_project()
    p1.transition_history.append("x")  # type: ignore
    assert p2.transition_history == []


def test_no_population_on_project():
    p = _make_project()
    assert not hasattr(p, "population")


def test_no_intervention_on_project():
    p = _make_project()
    assert not hasattr(p, "intervention")


def test_no_exposure_on_project():
    p = _make_project()
    assert not hasattr(p, "exposure")


def test_no_comparator_on_project():
    p = _make_project()
    assert not hasattr(p, "comparator")


def test_no_outcome_on_project():
    p = _make_project()
    assert not hasattr(p, "primary_outcome")
    assert not hasattr(p, "outcome")


def test_framework_is_optional():
    p = _make_project()
    p2 = _make_project(framework=ResearchFramework(type=FrameworkType.PICO))
    assert p.framework is None
    assert p2.framework is not None


def test_explicit_state_accepted_for_construction():
    p = _make_project(state=ResearchState.FRAMEWORK_DEFINED)
    assert p.state == ResearchState.FRAMEWORK_DEFINED
