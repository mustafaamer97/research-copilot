import streamlit as st

from src.services.literature_search_service import LiteratureSearchService
from src.adapters.pubmed_adapter import PubMedAdapter
from src.adapters.europe_pmc_adapter import EuropePMCAdapter
from src.adapters.openalex_adapter import OpenAlexAdapter
from src.adapters.crossref_adapter import CrossrefAdapter


st.set_page_config(
    page_title="Research Copilot",
    page_icon="🔬",
    layout="wide",
)


def build_search_service() -> LiteratureSearchService:
    """
    Build the literature search service with all currently supported providers.
    """

    adapters = [
        PubMedAdapter(),
        EuropePMCAdapter(),
        OpenAlexAdapter(),
        CrossrefAdapter(),
    ]

    return LiteratureSearchService(adapters=adapters)


def render_article(article) -> None:
    """Render a single literature result."""

    title = getattr(article, "title", None) or "Untitled article"

    with st.container():
        st.subheader(title)

        authors = getattr(article, "authors", None)
        if authors:
            if isinstance(authors, (list, tuple)):
                authors_text = ", ".join(str(author) for author in authors)
            else:
                authors_text = str(authors)

            st.write(f"**Authors:** {authors_text}")

        journal = getattr(article, "journal", None)
        if journal:
            st.write(f"**Journal:** {journal}")

        publication_date = getattr(article, "publication_date", None)
        if publication_date:
            st.write(f"**Publication date:** {publication_date}")

        doi = getattr(article, "doi", None)
        if doi:
            st.write(f"**DOI:** {doi}")

        pmid = getattr(article, "pmid", None)
        if pmid:
            st.write(f"**PMID:** {pmid}")

        abstract = getattr(article, "abstract", None)
        if abstract:
            with st.expander("Abstract"):
                st.write(abstract)

        url = getattr(article, "url", None)
        if url:
            st.link_button("Open article", url)

        st.divider()


def main() -> None:
    st.title("🔬 Research Copilot")
    st.caption(
        "Medical Research Assistant — Literature Search"
    )

    st.info(
        "AI assists the researcher; it does not replace the researcher's "
        "scientific judgment."
    )

    st.sidebar.header("Search settings")

    selected_sources = st.sidebar.multiselect(
        "Literature sources",
        options=[
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

    max_results = st.sidebar.number_input(
        "Maximum results per source",
        min_value=1,
        max_value=100,
        value=10,
        step=1,
    )

    deduplicate = st.sidebar.checkbox(
        "Remove duplicate articles",
        value=True,
    )

    query = st.text_area(
        "Research question / search query",
        placeholder=(
            "Example: laparoscopic appendectomy postoperative complications"
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
            ### Start your literature search

            Enter a research question or search query above, then choose
            the literature databases you want to search.

            The researcher remains responsible for interpreting and
            validating the evidence.
            """
        )
        return

    if not query.strip():
        st.warning("Please enter a research question or search query.")
        return

    if not selected_sources:
        st.warning("Please select at least one literature source.")
        return

    service = build_search_service()

    source_mapping = {
        "PubMed": PubMedAdapter,
        "Europe PMC": EuropePMCAdapter,
        "OpenAlex": OpenAlexAdapter,
        "Crossref": CrossrefAdapter,
    }

    adapters = []

    for source_name in selected_sources:
        adapter_class = source_mapping[source_name]

        try:
            adapters.append(adapter_class())
        except Exception as exc:
            st.error(
                f"Could not initialize {source_name}: {exc}"
            )

    if not adapters:
        st.error("No literature source could be initialized.")
        return

    service = LiteratureSearchService(adapters=adapters)

    with st.spinner("Searching the literature..."):
        try:
            result = service.search(
                query=query.strip(),
                max_results=max_results,
            )
        except TypeError:
            try:
                result = service.search(
                    query.strip(),
                    max_results=max_results,
                )
            except Exception as exc:
                st.error(f"Search failed: {exc}")
                return
        except Exception as exc:
            st.error(f"Search failed: {exc}")
            return

    if result is None:
        st.warning("No search result was returned.")
        return

    articles = getattr(result, "articles", None)

    if articles is None:
        articles = getattr(result, "records", None)

    if articles is None:
        if isinstance(result, (list, tuple)):
            articles = list(result)
        else:
            articles = []

    articles = list(articles)

    if deduplicate:
        seen = set()
        unique_articles = []

        for article in articles:
            doi = getattr(article, "doi", None)
            pmid = getattr(article, "pmid", None)
            title = getattr(article, "title", None)

            key = (
                str(doi).strip().lower()
                if doi
                else str(pmid).strip().lower()
                if pmid
                else str(title).strip().lower()
                if title
                else None
            )

            if key is None:
                unique_articles.append(article)
                continue

            if key in seen:
                continue

            seen.add(key)
            unique_articles.append(article)

        articles = unique_articles

    st.success(
        f"Found {len(articles)} unique article(s)."
    )

    if not articles:
        st.info(
            "No articles were found. Try a broader or differently worded query."
        )
        return

    st.header("Literature results")

    for index, article in enumerate(articles, start=1):
        st.markdown(f"### {index}")
        render_article(article)


if __name__ == "__main__":
    main()
