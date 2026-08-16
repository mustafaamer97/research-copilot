"""Tests for ActorType."""
from domain.actors import ActorType


def test_exact_actors_exist():
    values = {a.value for a in ActorType}
    assert values == {"RESEARCHER", "AI", "SYSTEM"}


def test_actor_count():
    assert len(ActorType) == 3


def test_actor_type_is_str_enum():
    assert isinstance(ActorType.RESEARCHER, str)
    assert ActorType.AI == "AI"
