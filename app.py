import streamlit as st

from adapters.pubmed import PubMedAdapter
from adapters.europe_pmc import EuropePMCAdapter
from adapters.openalex import OpenAlexAdapter
from adapters.crossref import CrossrefAdapter

from domain.literature_search import LiteratureSearchStrategy
from domain.framework import FrameworkType

from literature.orchestrator import LiteratureSearchOrchestrator

from infrastructure.sqlite_screening import (
    initialize_database as init_screening_db,
    save_decision,
    load_decisions,
)

from domain.evidence_extraction import (
    EvidenceExtraction,
    RiskOfBias,
)

from infrastructure.sqlite_extraction import (
    initialize_database as init_extraction_db,
    save_extraction,
)


st.set_page_config(
    page_title="Research Copilot",
    page_icon="🔬",
    layout="wide",
)


# ============================================================
# Helpers
# ============================================================

def create_search_strategy(query: str) -> LiteratureSearchStrategy:
    """
    Convert the researcher's query into the canonical
    LiteratureSearchStrategy used by the literature layer.
    """

    return LiteratureSearchStrategy(
        framework_type=FrameworkType.PICO,
        boolean_query=query.strip(),
    )


def get_value(obj, *names, default=None):
    """Safely read an attribute."""

    for name in names:

        if hasattr(obj, name):

            value = getattr(obj, name)

            if value is not None:
                return value

    return default


def render_article(article, index: int):
    """Render a single ResearchArticle."""

    title = get_value(
        article,
        "title",
        default="Untitled article",
    )

    authors = get_value(
        article,
        "authors",
        default=[],
    )

    journal = get_value(
        article,
        "journal",
        default=None,
    )

    publication_date = get_value(
        article,
        "publication_date",
        default=None,
    )

    doi = get_value(
        article,
        "doi",
        default=None,
    )

    pmid = get_value(
        article,
        "pmid",
        default=None,
    )

    abstract = get_value(
        article,
        "abstract",
        default=None,
    )

    url = get_value(
        article,
        "url",
        "source_url",
        default=None,
    )

    st.markdown(
        f"### {index}. {title}"
    )

    if authors:

        if isinstance(authors, (list, tuple)):
            authors_text = ", ".join(
                str(author)
                for author in authors
            )
        else:
            authors_text = str(authors)

        st.write(
            f"**Authors:** {authors_text}"
        )

    if journal:

        st.write(
            f"**Journal:** {journal}"
        )

    if publication_date:

        st.write(
            f"**Publication date:** "
            f"{publication_date}"
        )

    if doi:

        st.write(
            f"**DOI:** {doi}"
        )

    if pmid:

        st.write(
            f"**PMID:** {pmid}"
        )

    if abstract:

        with st.expander(
            "Abstract"
        ):
            st.write(abstract)

    if url:

        st.link_button(
            "Open article",
            url,
        )


def article_identity(article):
    """
    Return the strongest available identity for
    duplicate detection.
    """

    doi = get_value(
        article,
        "doi",
    )

    if doi:
        return (
            "doi",
            str(doi).strip().lower(),
        )

    pmid = get_value(
        article,
        "pmid",
    )

    if pmid:
        return (
            "pmid",
            str(pmid).strip().lower(),
        )

    title = get_value(
        article,
        "title",
    )

    if title:
        return (
            "title",
            str(title).strip().lower(),
        )

    return None


def deduplicate_articles(articles):
    """Remove duplicate articles."""

    unique_articles = []

    seen = set()

    for article in articles:

        identity = article_identity(
            article
        )

        if identity is None:

            unique_articles.append(
                article
            )

            continue

        if identity in seen:
            continue

        seen.add(identity)

        unique_articles.append(
            article
        )

    return unique_articles


# ============================================================
# Adapter configuration
# ============================================================

ADAPTER_CLASSES = {
    "PubMed": PubMedAdapter,
    "Europe PMC": EuropePMCAdapter,
    "OpenAlex": OpenAlexAdapter,
    "Crossref": CrossrefAdapter,
}


# ============================================================
# Main application
# ============================================================

def main():

    init_screening_db()
    init_extraction_db()

    if (
        "persisted_decisions_loaded"
        not in st.session_state
    ):

        persisted = load_decisions()

        st.session_state.persisted_decisions = persisted

        st.session_state.persisted_decisions_loaded = True

    st.title(
        "🔬 Research Copilot"
    )

    st.caption(
        "Medical Research Assistant — "
        "Literature Search"
    )

    st.info(
        "AI assists the researcher; it does not "
        "replace the researcher's scientific judgment."
    )

    # --------------------------------------------------------
    # Session State Initialization
    # --------------------------------------------------------

    if "articles" not in st.session_state:
        st.session_state.articles = None

    if "collection" not in st.session_state:
        st.session_state.collection = None

    if "raw_articles" not in st.session_state:
        st.session_state.raw_articles = []

    if "deduplicated_articles" not in st.session_state:
        st.session_state.deduplicated_articles = []

    if "active_query" not in st.session_state:
        st.session_state.active_query = ""

    if "active_sources" not in st.session_state:
        st.session_state.active_sources = []

    if "screening_decisions" not in st.session_state:
        st.session_state.screening_decisions = {}

    # --------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------

    st.sidebar.header(
        "Search settings"
    )

    selected_sources = st.sidebar.multiselect(
        "Literature sources",
        options=list(
            ADAPTER_CLASSES.keys()
        ),
        default=[
            "PubMed",
            "Europe PMC",
        ],
    )

    max_results = st.sidebar.number_input(
        "Maximum results",
        min_value=1,
        max_value=100,
        value=20,
        step=1,
        help=(
            "Maximum number of articles kept "
            "for the final result set."
        ),
    )

    deduplicate = st.sidebar.checkbox(
        "Remove duplicate articles",
        value=True,
    )

    # --------------------------------------------------------
    # Query
    # --------------------------------------------------------

    query = st.text_area(
        "Research question / search query",
        placeholder=(
            "Example: randomized controlled trials "
            "laparoscopic appendectomy children"
        ),
        height=120,
    )

    search_clicked = st.button(
        "🔎 Search literature",
        type="primary",
        use_container_width=True,
    )

    # --------------------------------------------------------
    # Search Execution
    # --------------------------------------------------------

    if search_clicked:

        clean_query = query.strip()

        if not clean_query:

            st.warning(
                "Please enter a research question "
                "or search query."
            )

            return

        if not selected_sources:

            st.warning(
                "Please select at least one "
                "literature source."
            )

            return

        strategy = create_search_strategy(
            clean_query
        )

        adapters = []

        for source_name in selected_sources:

            adapter_class = (
                ADAPTER_CLASSES[
                    source_name
                ]
            )

            try:

                adapters.append(
                    adapter_class()
                )

            except Exception as exc:

                st.error(
                    f"Could not initialize "
                    f"{source_name}: {exc}"
                )

        if not adapters:

            st.error(
                "No literature source could "
                "be initialized."
            )

            return

        with st.spinner(
            "Searching the literature..."
        ):

            try:

                orchestrator = (
                    LiteratureSearchOrchestrator(
                        adapters=adapters
                    )
                )

                collection = (
                    orchestrator.search(
                        strategy
                    )
                )

                raw_articles = list(
                    collection.all_records
                )

                if deduplicate:

                    deduplicated_articles = (
                        deduplicate_articles(
                            raw_articles
                        )
                    )

                else:

                    deduplicated_articles = raw_articles

                articles = deduplicated_articles[
                    : int(max_results)
                ]

                # Store all search results in session state
                st.session_state.collection = collection
                st.session_state.raw_articles = raw_articles
                st.session_state.deduplicated_articles = deduplicated_articles
                st.session_state.articles = articles
                st.session_state.active_query = clean_query
                st.session_state.active_sources = selected_sources
                st.session_state.screening_decisions = {}

            except Exception as exc:

                st.error(
                    f"Literature search failed: {exc}"
                )

                st.exception(exc)

                return

    # --------------------------------------------------------
    # Check if we have active search results
    # --------------------------------------------------------

    if st.session_state.articles is None:

        st.markdown(
            """
            ## Start your literature search

            Enter a research question or search query above.

            Then select the literature sources you want to search.

            The researcher remains responsible for interpreting
            and validating the evidence.
            """
        )

        return

    # Fetch active data from state
    articles = st.session_state.articles
    collection = st.session_state.collection
    raw_articles = st.session_state.raw_articles
    deduplicated_articles = st.session_state.deduplicated_articles
    active_sources = st.session_state.active_sources
    active_query = st.session_state.active_query

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    st.success(
        f"Search completed — "
        f"{len(articles)} article(s) shown."
    )

    st.caption(
        f"Query: {active_query}"
    )

    # --------------------------------------------------------
    # Search summary
    # --------------------------------------------------------

    st.subheader(
        "Search summary"
    )

    columns = st.columns(
        len(active_sources)
    )

    for column, source_name in zip(
        columns,
        active_sources,
    ):

        source_count = 0

        for result in collection.results:

            source_value = getattr(
                result.source,
                "value",
                str(result.source),
            )

            if (
                source_value.lower()
                == source_name.lower()
            ):

                source_count += len(
                    result.records
                )

        column.metric(
            source_name,
            source_count,
        )

    # --------------------------------------------------------
    # Raw vs final result count
    # --------------------------------------------------------

    with st.expander(
        "Search diagnostics"
    ):

        st.write(
            f"Raw records returned: "
            f"{len(raw_articles)}"
        )

        st.write(
            f"After deduplication: "
            f"{len(deduplicated_articles)}"
        )

        st.write(
            f"Maximum displayed: "
            f"{len(articles)}"
        )

    # --------------------------------------------------------
    # Failures
    # --------------------------------------------------------

    if collection and collection.failures:

        with st.expander(
            "⚠️ Sources with errors"
        ):

            for failure in (
                collection.failures
            ):

                st.warning(
                    f"{failure.adapter_name}: "
                    f"{failure.error}"
                )

    # --------------------------------------------------------
    # Empty result
    # --------------------------------------------------------

    if not articles:

        st.info(
            "No articles were found. "
            "Try a broader or differently "
            "worded query."
        )

        return

    # --------------------------------------------------------
    # Screening Dashboard
    # --------------------------------------------------------

    st.markdown("---")

    included_count = sum(
        1
        for value in st.session_state.screening_decisions.values()
        if value["decision"] == "Include"
    )

    excluded_count = sum(
        1
        for value in st.session_state.screening_decisions.values()
        if value["decision"] == "Exclude"
    )

    maybe_count = sum(
        1
        for value in st.session_state.screening_decisions.values()
        if value["decision"] == "Maybe"
    )

    screened_count = len(
        st.session_state.screening_decisions
    )

    remaining_count = max(
        0,
        len(articles) - screened_count
    )

    completion_percent = round(
        (screened_count / len(articles)) * 100,
        1,
    ) if articles else 0

    st.subheader("Screening Dashboard")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Total", len(articles))
    c2.metric("Screened", screened_count)
    c3.metric("Included", included_count)
    c4.metric("Excluded", excluded_count)
    c5.metric("Maybe", maybe_count)
    c6.metric("Remaining", remaining_count)

    st.progress(
        completion_percent / 100
    )

    st.caption(
        f"Completion: {completion_percent}%"
    )

    # --------------------------------------------------------
    # Tabs
    # --------------------------------------------------------

    tab_all, tab_included, tab_excluded, tab_maybe = st.tabs(
        [
            "📄 All",
            "✅ Included",
            "❌ Excluded",
            "🟡 Maybe",
        ]
    )

    # --------------------------------------------------------
    # All Studies
    # --------------------------------------------------------

    with tab_all:

        for index, article in enumerate(
            articles,
            start=1,
        ):

            render_article(
                article,
                index,
            )

            article_key = f"article_{index}"

            existing = (
                st.session_state
                .screening_decisions
                .get(article_key)
            )

            saved_decision = (
                st.session_state
                .persisted_decisions
                .get(article_key, {})
                .get("decision")
            )

            default_index = None

            if saved_decision == "Include":
                default_index = 0

            elif saved_decision == "Exclude":
                default_index = 1

            elif saved_decision == "Maybe":
                default_index = 2

            decision = st.radio(
                f"Decision #{index}",
                [
                    "Include",
                    "Exclude",
                    "Maybe",
                ],
                key=f"decision_{index}",
                index=default_index,
            )

            exclusion_reason = None

            if decision == "Exclude":

                exclusion_reason = st.selectbox(
                    f"Reason #{index}",
                    [
                        "Wrong Population",
                        "Wrong Intervention",
                        "Wrong Outcome",
                        "Wrong Study Design",
                        "Animal Study",
                        "Not Original Research",
                        "Other",
                    ],
                    key=f"reason_{index}",
                )

            if st.button(
                f"Save Decision #{index}",
                key=f"save_{index}",
            ):

                st.session_state.screening_decisions[
                    article_key
                ] = {
                    "article": article,
                    "decision": decision,
                    "reason": exclusion_reason,
                }

                save_decision(
                    article_key=article_key,
                    article=article,
                    decision=decision,
                    reason=exclusion_reason,
                )

                st.rerun()

            if existing:

                message = (
                    f"Saved Decision: "
                    f"{existing['decision']}"
                )

                if existing["reason"]:

                    message += (
                        f" | Reason: "
                        f"{existing['reason']}"
                    )

                st.info(message)

            st.divider()

    # --------------------------------------------------------
    # Included
    # --------------------------------------------------------

    with tab_included:

        for idx, (key, value) in enumerate(
            st.session_state.screening_decisions.items(),
            start=1
        ):

            if value["decision"] == "Include":

                art = value.get("article")

                if art:
                    render_article(art, idx)
                else:
                    st.success(key)

                st.success("Current Decision: Include")

                with st.expander(
                    f"Evidence Extraction #{idx}"
                ):

                    population = st.text_area(
                        "Population",
                        key=f"population_{key}",
                    )

                    intervention = st.text_area(
                        "Intervention",
                        key=f"intervention_{key}",
                    )

                    comparator = st.text_area(
                        "Comparator",
                        key=f"comparator_{key}",
                    )

                    outcome = st.text_area(
                        "Outcome",
                        key=f"outcome_{key}",
                    )

                    study_design = st.selectbox(
                        "Study Design",
                        [
                            "Randomized Controlled Trial (RCT)",
                            "Non-Randomized Trial",
                            "Cohort Study",
                            "Case-Control Study",
                            "Cross-Sectional Study",
                            "Systematic Review",
                            "Meta-Analysis",
                            "Case Series",
                            "Case Report",
                            "Qualitative Study",
                            "Other",
                        ],
                        key=f"study_design_{key}",
                    )

                    risk_of_bias = st.selectbox(
                        "Risk of Bias *",
                        [
                            "Low",
                            "Some Concerns",
                            "High",
                        ],
                        key=f"risk_of_bias_{key}",
                    )

                    sample_size = st.number_input(
                        "Sample Size *",
                        min_value=0,
                        step=1,
                        key=f"sample_size_{key}",
                    )

                    funding_source = st.text_input(
                        "Funding Source",
                        key=f"funding_source_{key}",
                    )

                    conflict_of_interest = st.selectbox(
                        "Conflict of Interest",
                        [
                            "Declared",
                            "Not Declared",
                            "Unclear",
                        ],
                        key=f"conflict_of_interest_{key}",
                    )

                    follow_up_duration = st.text_input(
                        "Follow-up Duration",
                        placeholder="e.g. 12 months",
                        key=f"follow_up_duration_{key}",
                    )

                    notes = st.text_area(
                        "Notes",
                        key=f"notes_{key}",
                    )

                    st.caption(
                        "Required fields: Risk of Bias and Sample Size"
                    )

                    save_extraction_clicked = st.button(
                        f"Save Extraction #{idx}",
                        key=f"save_extraction_{key}",
                    )

                    if save_extraction_clicked:

                        if not risk_of_bias:

                            st.error(
                                "Risk of Bias is required."
                            )

                        else:

                            article_id = getattr(
                                art,
                                "id",
                                getattr(
                                    art,
                                    "pmid",
                                    getattr(
                                        art,
                                        "doi",
                                        key,
                                    ),
                                ),
                            )

                            if article_id is None:

                                st.error(
                                    "Article ID not found."
                                )

                            else:

                                extraction = EvidenceExtraction(
                                    article_id=article_id,

                                    doi=getattr(
                                        art,
                                        "doi",
                                        None,
                                    ),

                                    pmid=getattr(
                                        art,
                                        "pmid",
                                        None,
                                    ),

                                    population=population,

                                    intervention=intervention,

                                    comparator=comparator,

                                    outcome=outcome,

                                    study_design=study_design,

                                    risk_of_bias=RiskOfBias(
                                        risk_of_bias
                                    ),

                                    sample_size=int(
                                        sample_size
                                    ),

                                    funding_source=funding_source,

                                    conflict_of_interest=conflict_of_interest,

                                    follow_up_duration=follow_up_duration,

                                    notes=notes,
                                )

                                save_extraction(
                                    extraction
                                )

                                st.success(
                                    "Evidence extraction saved to SQLite."
                                )

                c1, c2 = st.columns(2)

                if c1.button(
                    f"Move To Exclude #{idx}",
                    key=f"inc_to_exc_{idx}",
                ):
                    value["decision"] = "Exclude"
                    value["reason"] = "Changed During Review"
                    st.rerun()

                if c2.button(
                    f"Move To Maybe #{idx}",
                    key=f"inc_to_maybe_{idx}",
                ):
                    value["decision"] = "Maybe"
                    value["reason"] = None
                    st.rerun()

                st.divider()

    # --------------------------------------------------------
    # Excluded
    # --------------------------------------------------------

    with tab_excluded:

        for idx, (key, value) in enumerate(
            st.session_state.screening_decisions.items(),
            start=1
        ):

            if value["decision"] == "Exclude":

                st.error(
                    f"Reason: {value['reason']}"
                )

                art = value.get("article")

                if art:
                    render_article(art, idx)
                else:
                    st.write(key)

                c1, c2 = st.columns(2)

                if c1.button(
                    f"Move To Include #{idx}",
                    key=f"exc_to_inc_{idx}",
                ):
                    value["decision"] = "Include"
                    value["reason"] = None
                    st.rerun()

                if c2.button(
                    f"Move To Maybe #{idx}",
                    key=f"exc_to_maybe_{idx}",
                ):
                    value["decision"] = "Maybe"
                    value["reason"] = None
                    st.rerun()

                st.divider()

    # --------------------------------------------------------
    # Maybe
    # --------------------------------------------------------

    with tab_maybe:

        for idx, (key, value) in enumerate(
            st.session_state.screening_decisions.items(),
            start=1
        ):

            if value["decision"] == "Maybe":

                art = value.get("article")

                if art:
                    render_article(art, idx)
                else:
                    st.warning(key)

                st.warning("Current Decision: Maybe")

                c1, c2 = st.columns(2)

                if c1.button(
                    f"Move To Include #{idx}",
                    key=f"maybe_to_inc_{idx}",
                ):
                    value["decision"] = "Include"
                    value["reason"] = None
                    st.rerun()

                if c2.button(
                    f"Move To Exclude #{idx}",
                    key=f"maybe_to_exc_{idx}",
                ):
                    value["decision"] = "Exclude"
                    value["reason"] = "Changed During Review"
                    st.rerun()

                st.divider()


if __name__ == "__main__":
    main()
