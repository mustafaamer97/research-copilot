"""Canonical transition graph and structural transition validation."""
from domain.state import ResearchState

ALLOWED_TRANSITIONS: dict[ResearchState, ResearchState] = {
    ResearchState.IDEA: ResearchState.QUESTION_DEFINED,
    ResearchState.QUESTION_DEFINED: ResearchState.FRAMEWORK_DEFINED,
    ResearchState.FRAMEWORK_DEFINED: ResearchState.DESIGN_SELECTED,
    ResearchState.DESIGN_SELECTED: ResearchState.PROTOCOL_READY,
    ResearchState.PROTOCOL_READY: ResearchState.LITERATURE_SEARCH,
    ResearchState.LITERATURE_SEARCH: ResearchState.SCREENING,
    ResearchState.SCREENING: ResearchState.DATA_COLLECTION,
    ResearchState.DATA_COLLECTION: ResearchState.DATA_READY,
    ResearchState.DATA_READY: ResearchState.ANALYSIS_PLAN_LOCKED,
    ResearchState.ANALYSIS_PLAN_LOCKED: ResearchState.ANALYSIS_COMPLETE,
    ResearchState.ANALYSIS_COMPLETE: ResearchState.MANUSCRIPT_DRAFT,
    ResearchState.MANUSCRIPT_DRAFT: ResearchState.AUDIT,
    ResearchState.AUDIT: ResearchState.JOURNAL_SELECTION,
    ResearchState.JOURNAL_SELECTION: ResearchState.READY_FOR_SUBMISSION,
}


def is_transition_allowed(from_state: ResearchState, to_state: ResearchState) -> bool:
    return ALLOWED_TRANSITIONS.get(from_state) == to_state
