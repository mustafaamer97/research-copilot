"""Tests for ResearchQuestion."""
import pytest
from domain.research_question import ResearchQuestion


def test_valid_question_accepted():
    q = ResearchQuestion(text="Does intervention X reduce outcome Y?")
    assert q.text == "Does intervention X reduce outcome Y?"


def test_empty_question_rejected():
    with pytest.raises(Exception):
        ResearchQuestion(text="")


def test_whitespace_only_question_rejected():
    with pytest.raises(Exception):
        ResearchQuestion(text="   ")


def test_question_not_mutated():
    q = ResearchQuestion(text="Valid question?")
    assert q.text == "Valid question?"
