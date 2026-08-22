import streamlit as st

from literature.orchestrator import LiteratureSearchOrchestrator
from adapters.pubmed import PubMedAdapter
from adapters.europe_pmc import EuropePMCAdapter
from adapters.openalex import OpenAlexAdapter
from adapters.crossref import CrossrefAdapter


st.set_page_config(
    page_title="Research Copilot",
    page_icon="🔬",
    layout="wide",
)


def build_adapters():
    """Create the available literature adapters."""

    return {
        "PubMed": PubMedAdapter(),
        "Europe PMC": EuropePMCAdapter(),
        "OpenAlex": OpenAlexAdapter(),
        "Crossref": CrossrefAdapter(),
    }


def get_value(obj, *names, default=None):
    """Safely retrieve an attribute from an object."""

    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value

    return default


def render_article(article, index):
    """Render one literature article."""

    title = get_value(
        article,
        "title",
        default="Untitled article",
    )

    st.markdown(f"### {index}. {title}")

    authors = get_value(article, "authors")

    if authors:
        if isinstance(authors, (list, tuple)):
            authors_text = ", ".join(str(author) for author in authors)
        else:
            authors_text = str(authors)

        st.write(f"**Authors:** {authors_text}")

    journal = get_value(
        article,
        "journal",
        "journal_name",
    )

    if journal:
        st.write(f"**Journal:** {journal}")

    publication_date = get_value(
        article,
        "publication_date",
        "published_date",
        "date",
    )

    if publication_date:
        st.write(f"**Publication date:** {publication_date}")

    doi = get_value(article, "doi")

    if doi:
        st.write(f"**DOI:** {doi}")

    pmid = get_value(article, "pmid")

    if pmid:
        st.write(f"**PMID:** {pmid}")

    abstract = get_value(article, "abstract")

    if abstract:
        with st.expander("Abstract"):
            st.write(abstract)

    url = get_value(
        article,
        "url",
        "link",
    )

    if url:
        st.link_button(
            "Open article",
            url,
        )

    st.divider()


def main():
    st.title("🔬 Research Copilot")

    st.caption(
        "Medical Research Assistant — Literature Search"
    )

    st.info(
        "AI assists the researcher; it does not replace "
        "the researcher's scientific judgment."
    )

    st.sidebar.header("Search settings")

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

    adapters = build_adapters()

    selected_adapters = [
        adapters[source]
        for source in selected_sources
    ]

    try:
        orchestrator = LiteratureSearchOrchestrator(
            adapters=selected_adapters
        )
    except TypeError:
        try:
            orchestrator = LiteratureSearchOrchestrator(
                selected_adapters
            )
        except Exception as exc:
            st.error(
                f"Could not initialize literature search: {exc}"
            )
            return

    with st.spinner("Searching the literature..."):

        try:
            result = orchestrator.search(
                query=query.strip(),
                max_results=max_results,
            )

        except TypeError:

            try:
                result = orchestrator.search(
                    query.strip(),
                    max_results,
                )

            except Exception as exc:
                st.error(
                    f"Literature search failed: {exc}"
                )
                return

        except Exception as exc:
            st.error(
                f"Literature search failed: {exc}"
            )
            return

    if result is None:
        st.warning(
            "No result was returned."
        )
        return

    if isinstance(result, (list, tuple)):
        articles = list(result)

    else:
        articles = get_value(
            result,
            "articles",
            "records",
            "results",
            default=[],
        )

        if articles is None:
            articles = []

        articles = list(articles)

    if deduplicate:
        unique_articles = []
        seen = set()

        for article in articles:

            doi = get_value(article, "doi")
            pmid = get_value(article, "pmid")
            title = get_value(article, "title")

            if doi:
                key = f"doi:{str(doi).strip().lower()}"

            elif pmid:
                key = f"pmid:{str(pmid).strip().lower()}"

            elif title:
                key = (
                    f"title:"
                    f"{str(title).strip().lower()}"
                )

            else:
                key = None

            if key is None:
                unique_articles.append(article)
                continue

            if key in seen:
                continue

            seen.add(key)
            unique_articles.append(article)

        articles = unique_articles

    st.success(
        f"Found {len(articles)} article(s)."
    )

    if not articles:
        st.info(
            "No articles were found. "
            "Try a broader or differently worded query."
        )

        return

    st.header("Literature results")

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
