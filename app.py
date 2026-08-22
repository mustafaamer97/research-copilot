import streamlit as st

from adapters.pubmed import PubMedAdapter
from adapters.europe_pmc import EuropePMCAdapter
from adapters.openalex import OpenAlexAdapter
from adapters.crossref import CrossrefAdapter

from domain.literature_search import LiteratureSearchStrategy
from domain.framework import FrameworkType

from literature.orchestrator import LiteratureSearchOrchestrator


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

    st.divider()


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

    if not search_clicked:

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

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    query = query.strip()

    if not query:

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

    # --------------------------------------------------------
    # Strategy
    # --------------------------------------------------------

    strategy = create_search_strategy(
        query
    )

    # --------------------------------------------------------
    # Adapters
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

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

        except Exception as exc:

            st.error(
                f"Literature search failed: {exc}"
            )

            st.exception(exc)

            return

    # --------------------------------------------------------
    # Raw results
    # --------------------------------------------------------

    raw_articles = list(
        collection.all_records
    )

    # --------------------------------------------------------
    # Deduplication
    # --------------------------------------------------------

    if deduplicate:

        articles = deduplicate_articles(
            raw_articles
        )

    else:

        articles = raw_articles

    # --------------------------------------------------------
    # FINAL LIMIT
    #
    # This is deliberately applied AFTER
    # deduplication so the UI has a strict
    # maximum result count.
    # --------------------------------------------------------

    articles = articles[
        : int(max_results)
    ]

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    st.success(
        f"Search completed — "
        f"{len(articles)} article(s) shown."
    )

    st.caption(
        f"Query: {query}"
    )

    # --------------------------------------------------------
    # Search summary
    # --------------------------------------------------------

    st.subheader(
        "Search summary"
    )

    columns = st.columns(
        len(selected_sources)
    )

    for column, source_name in zip(
        columns,
        selected_sources,
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
            f"{len(articles)}"
        )

        st.write(
            f"Maximum displayed: "
            f"{int(max_results)}"
        )

    # --------------------------------------------------------
    # Failures
    # --------------------------------------------------------

    if collection.failures:

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
    # Results
    # --------------------------------------------------------

    st.subheader(
        "Literature results"
    )

    for index, article in enumerate(
        articles,
        start=1,
    ):

        render_article(
            article,
            index,
        )


if __name__ == "__main__":
    main()
