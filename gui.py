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
            st.success(f"Found {len(fetched_articles)} articles.")

            # Diagnostic & Normalization Inspection View
            st.subheader("🔍 Article Attributes & Data Inspection")
            
            for i, article in enumerate(fetched_articles, 1):
                # Safe extraction attempts
                title = getattr(article, "title", None) or getattr(article, "paper_title", None) or "Untitled Article"
                doi = getattr(article, "doi", None) or getattr(article, "identifier", None) or "N/A"
                
                with st.expander(f"{i}. {title}"):
                    st.write(f"**DOI:** {doi}")
                    st.write("**Object Type:**", type(article).__name__)
                    st.write("**Raw Object Properties (vars):**")
                    
                    # Display full internal structure of the article object
                    if hasattr(article, "__dict__"):
                        st.json(vars(article))
                    else:
                        st.write(article)
        else:
            st.warning("No results found matching your query.")
