"""Deterministic literature search strategy builder."""
from domain.framework import FrameworkType
from domain.literature_search import LiteratureSearchStrategy


class SearchStrategyValidationError(ValueError):
    """Raised when required search terms are missing for the requested framework."""


def _quote_term(term: str) -> str:
    """Wrap a term in double-quotes, escaping any embedded double-quotes."""
    escaped = term.replace('"', '\\"')
    return f'"{escaped}"'


def _build_component_clause(terms: list[str]) -> str | None:
    """Return a Boolean clause for one component, or None if terms is empty."""
    if not terms:
        return None
    quoted = [_quote_term(t) for t in terms]
    if len(quoted) == 1:
        return f"({quoted[0]})"
    return "(" + " OR ".join(quoted) + ")"


def _build_boolean_query(clauses: list[str]) -> str:
    return " AND ".join(clauses)


def build_search_strategy(
    framework_type: FrameworkType,
    population_terms: list[str] | None = None,
    intervention_terms: list[str] | None = None,
    exposure_terms: list[str] | None = None,
    comparator_terms: list[str] | None = None,
    outcome_terms: list[str] | None = None,
) -> LiteratureSearchStrategy:
    """
    Build a LiteratureSearchStrategy from explicitly supplied researcher terms.

    Never invents synonyms, MeSH terms, or extra terms.
    Never calls external APIs or AI.
    Never mutates any domain object.
    """
    pop = list(population_terms) if population_terms is not None else []
    intv = list(intervention_terms) if intervention_terms is not None else []
    expo = list(exposure_terms) if exposure_terms is not None else []
    comp = list(comparator_terms) if comparator_terms is not None else []
    outc = list(outcome_terms) if outcome_terms is not None else []

    if framework_type == FrameworkType.PICO:
        _validate_pico(pop, intv, comp, outc)
        return _build_pico(pop, intv, comp, outc)

    if framework_type == FrameworkType.PECO:
        _validate_peco(pop, expo, comp, outc)
        return _build_peco(pop, expo, comp, outc)

    raise SearchStrategyValidationError(
        f"Unsupported framework type: {framework_type}"
    )


# ---------------------------------------------------------------------------
# PICO
# ---------------------------------------------------------------------------

def _validate_pico(
    pop: list[str],
    intv: list[str],
    comp: list[str],
    outc: list[str],
) -> None:
    missing = []
    if not pop:
        missing.append("population_terms")
    if not intv:
        missing.append("intervention_terms")
    if not comp:
        missing.append("comparator_terms")
    if not outc:
        missing.append("outcome_terms")
    if missing:
        raise SearchStrategyValidationError(
            f"PICO search strategy requires: {', '.join(missing)}."
        )


def _build_pico(
    pop: list[str],
    intv: list[str],
    comp: list[str],
    outc: list[str],
) -> LiteratureSearchStrategy:
    clauses = []
    for terms in (pop, intv, comp, outc):
        clause = _build_component_clause(terms)
        if clause:
            clauses.append(clause)
    query = _build_boolean_query(clauses)
    return LiteratureSearchStrategy(
        framework_type=FrameworkType.PICO,
        population_terms=pop,
        intervention_terms=intv,
        comparator_terms=comp,
        outcome_terms=outc,
        boolean_query=query,
    )


# ---------------------------------------------------------------------------
# PECO
# ---------------------------------------------------------------------------

def _validate_peco(
    pop: list[str],
    expo: list[str],
    comp: list[str],
    outc: list[str],
) -> None:
    missing = []
    if not pop:
        missing.append("population_terms")
    if not expo:
        missing.append("exposure_terms")
    if not comp:
        missing.append("comparator_terms")
    if not outc:
        missing.append("outcome_terms")
    if missing:
        raise SearchStrategyValidationError(
            f"PECO search strategy requires: {', '.join(missing)}."
        )


def _build_peco(
    pop: list[str],
    expo: list[str],
    comp: list[str],
    outc: list[str],
) -> LiteratureSearchStrategy:
    clauses = []
    for terms in (pop, expo, comp, outc):
        clause = _build_component_clause(terms)
        if clause:
            clauses.append(clause)
    query = _build_boolean_query(clauses)
    return LiteratureSearchStrategy(
        framework_type=FrameworkType.PECO,
        population_terms=pop,
        exposure_terms=expo,
        comparator_terms=comp,
        outcome_terms=outc,
        boolean_query=query,
    )
