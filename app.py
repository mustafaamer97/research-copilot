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
    Convert the researcher's text query into the canonical
    LiteratureSearchStrategy used by all literature adapters.
    """

    return LiteratureSearchStrategy(
        framework_type=FrameworkType.PICO,
        boolean_query=query.strip(),
    )


def get_article_value(article, *names, default=None):
    """Safely read a value from a ResearchArticle."""

    for name in names:
        if hasattr(article, name):
            value = getattr(article, name)

            if value is not None:
                return value

    return default


def render_article(article, index: int) -> None:
    """Render one ResearchArticle."""

    title = get_article_value(
        article,
        "title",
        default="Untitled article",
    )

    authors = get_article_value(
        article,
        "authors",
        default=[],
    )

    journal = get_article_value(
        article,
        "journal",
        default=None,
    )

    publication_date = get_article_value(
        article,
        "publication_date",
        default=None,
    )

    doi = get_article_value(
        article,
        "doi",
        default=None,
    )

    pmid = get_article_value(
        article,
        "pmid",
        default=None,
    )

    abstract = get_article_value(
        article,
        "abstract",
        default=None,
    )

    url = get_article_value(
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
            f"**Publication date:** {publication_date}"
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

        with st.expander("Abstract"):
            st.write(abstract)

    if url:

        st.link_button(
            "Open article",
            url,
        )

    st.divider()


def deduplicate_articles(articles):
    """
    Remove duplicate articles using DOI, PMID,
    then title as fallback.
    """

    unique_articles = []
    seen = set()

    for article in articles:

        doi = get_article_value(
            article,
            "doi",
        )

        pmid = get_article_value(
            article,
            "pmid",
        )

        title = get_article_value(
            article,
            "title",
        )

        if doi:

            key = (
                "doi:",
                str(doi).strip().lower(),
            )

        elif pmid:

            key = (
                "pmid:",
                str(pmid).strip().lower(),
            )

        elif title:

            key = (
                "title:",
                str(title).strip().lower(),
            )

        else:

            unique_articles.append(article)
            continue

        if key in seen:
            continue

        seen.add(key)

        unique_articles.append(article)

    return unique_articles


# ============================================================
# Streamlit UI
# ============================================================

def main():

    st.title(
        "🔬 Research Copilot"
    )

    st.caption(
        "Medical Research Assistant — Literature Search"
    )

    st.info(
        "AI assists the researcher; it does not replace "
        "the researcher's scientific judgment."
    )

    # --------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------

    st.sidebar.header(
        "Search settings"
    )

    selected_sources = st.sidebar.multiselect(
        "Literature sources",
        [
            "PubMed",
            "Europe PMC",
            "OpenAlex",
            "Crossref",
        ],
        default=[
            "PubMed",
            "Europe PMC",
        ],
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
            "Example: laparoscopic appendectomy "
            "postoperative complications"
        ),
        height=120,
    )

    search_clicked = st.button(
        "🔎 Search literature",
        type="primary",
        use_container_width=True,
    )

    # --------------------------------------------------------
    # Initial screen
    # --------------------------------------------------------

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

    if not query.strip():

        st.warning(
            "Please enter a research question or search query."
        )

        return

    if not selected_sources:

        st.warning(
            "Please select at least one literature source."
        )

        return

    # --------------------------------------------------------
    # Create strategy
    # --------------------------------------------------------

    strategy = create_search_strategy(
        query
    )

    # --------------------------------------------------------
    # Create adapters
    # --------------------------------------------------------

    adapter_classes = {
        "PubMed": PubMedAdapter,
        "Europe PMC": EuropePMCAdapter,
        "OpenAlex": OpenAlexAdapter,
        "Crossref": CrossrefAdapter,
    }

    adapters = []

    for source_name in selected_sources:

        adapter_class = adapter_classes[
            source_name
        ]

        try:

            adapter = adapter_class()

            adapters.append(adapter)

        except Exception as exc:

            st.error(
                f"Could not initialize "
                f"{source_name}: {exc}"
            )

    if not adapters:

        st.error(
            "No literature source could be initialized."
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

            collection = orchestrator.search(
                strategy
            )

        except Exception as exc:

            st.error(
                f"Literature search failed: {exc}"
            )

            st.exception(exc)

            return

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    articles = collection.all_records

    if deduplicate:

        articles = deduplicate_articles(
            articles
        )

    # --------------------------------------------------------
    # Search summary
    # --------------------------------------------------------

    st.success(
        f"Search completed — "
        f"{len(articles)} article(s) available."
    )

    # --------------------------------------------------------
    # Source results
    # --------------------------------------------------------

    st.subheader(
        "Search summary"
    )

    summary_columns = st.columns(
        len(selected_sources)
    )

    for column, source_name in zip(
        summary_columns,
        selected_sources,
    ):

        source_results = [
            result
            for result in collection.results
            if result.source.value == source_name
            or result.source.name == source_name.upper().replace(
                " ",
                "_",
            )
        ]

        count = sum(
            len(result.records)
            for result in source_results
        )

        column.metric(
            source_name,
            count,
        )

    # --------------------------------------------------------
    # Failures
    # --------------------------------------------------------

    if collection.failures:

        with st.expander(
            "⚠️ Sources with errors"
        ):

            for failure in collection.failures:

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
            "Try a broader or differently worded query."
        )

        return

    # --------------------------------------------------------
    # Render
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
