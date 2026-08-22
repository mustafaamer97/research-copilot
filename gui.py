import streamlit as st
import asyncio

from adapters.pubmed import PubMedAdapter
from adapters.europe_pmc import EuropePMCAdapter
from adapters.openalex import OpenAlexAdapter

from domain.literature_search import LiteratureSearchStrategy
from domain.framework import FrameworkType

# Page Configuration
st.set_page_config(
    page_title="Research Copilot",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 Research Copilot - Medical Research Assistant")
st.markdown("Welcome! Search medical literature seamlessly across global databases.")

# Sidebar Configuration
st.sidebar.header("Search Settings")
selected_sources = st.sidebar.multiselect(
    "Select Literature Sources:",
    ["PubMed", "Europe PMC", "OpenAlex"],
    default=["PubMed", "Europe PMC"]
)

# Main Query Input
query = st.text_input(
    "Enter medical keywords (e.g., Appendicitis, Laparoscopic surgery):",
    ""
)

def create_search_strategy(user_query: str):
    """
    Wrap user text into a LiteratureSearchStrategy Query Object
    """
    return LiteratureSearchStrategy(
        framework_type=FrameworkType.PICO,
        boolean_query=user_query
    )

async def run_adapter(adapter, strategy):
    """
    Execute adapter search whether async or sync
    """
    try:
        result = adapter.search(strategy)
        if asyncio.iscoroutine(result):
            result = await result
        return result or []
    except Exception as e:
        raise e

if st.button("Start Combined Search 🚀", type="primary"):
    if not query.strip():
        st.warning("Please enter a valid search query.")
    else:
        st.info(f"Searching for: **{query}** ...")

        async def fetch_all():
            all_articles = []
            strategy = create_search_strategy(query)

            sources = {
                "PubMed": PubMedAdapter,
                "Europe PMC": EuropePMCAdapter,
                "OpenAlex": OpenAlexAdapter
            }

            for source_name, adapter_class in sources.items():
                if source_name not in selected_sources:
                    continue

                try:
                    adapter = adapter_class()
                    results = await run_adapter(adapter, strategy)
                    if results:
                        all_articles.extend(results)
                except Exception as e:
                    st.error(f"Error in {source_name}: {str(e)}")

            return all_articles

        with st.spinner("Fetching research articles..."):
            fetched_articles = asyncio.run(fetch_all())

        if fetched_articles:
            st.success(f"Found results from {len(fetched_articles)} sources.")

            # Article Extraction and Rendering
            for i, article in enumerate(fetched_articles, 1):
                
                # Handling Tuple output from specific adapters
                if isinstance(article, tuple):
                    key, value = article
                    if key == "records":
                        articles = value
                    else:
                        articles = []
                else:
                    articles = [article]

                # Render each record
                for record in articles:
                    title = getattr(record, "title", "Untitled Article")
                    abstract = getattr(record, "abstract", "No abstract available.")
                    doi = getattr(record, "doi", "N/A")
                    journal = getattr(record, "journal", "Unknown Journal")
                    authors = getattr(record, "authors", [])

                    # Ensure authors is iterable (list of strings)
                    if not isinstance(authors, list):
                        authors = [str(authors)] if authors else []
                    
                    authors_str = ", ".join(str(a) for a in authors) if authors else "Unknown Authors"

                    with st.expander(f"{title}"):
                        st.write(f"**Journal:** {journal}")
                        st.write(f"**Authors:** {authors_str}")
                        st.write(f"**DOI:** {doi}")
                        st.write("**Abstract:**")
                        st.write(abstract)

        else:
            st.warning("No results found matching your query.")
