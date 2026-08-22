import streamlit as st
import asyncio

from adapters.pubmed import PubMedAdapter
from adapters.europe_pmc import EuropePMCAdapter
from adapters.openalex import OpenAlexAdapter

from domain.literature_search import LiteratureSearchStrategy
from domain.framework import FrameworkType


# إعدادات الصفحة
st.set_page_config(
    page_title="Research Copilot",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 Research Copilot - المساعد البحثي الطبي")
st.markdown("مرحباً بك! يمكنك البحث في قواعد البيانات الطبية العالمية بسهولة.")


# القائمة الجانبية
st.sidebar.header("إعدادات البحث")

selected_sources = st.sidebar.multiselect(
    "اختر المصادر البحثية:",
    ["PubMed", "Europe PMC", "OpenAlex"],
    default=["PubMed", "Europe PMC"]
)


# مربع البحث
query = st.text_input(
    "أدخل الكلمات المفتاحية للبحث الطبي:",
    ""
)


def create_search_strategy(user_query: str):
    """
    تحويل النص القادم من المستخدم إلى Query Object
    """
    return LiteratureSearchStrategy(
        framework_type=FrameworkType.PICO,
        boolean_query=user_query
    )


async def run_adapter(adapter, strategy):
    """
    تشغيل الـ adapter سواء كان async أو sync
    """
    try:
        result = adapter.search(strategy)

        if asyncio.iscoroutine(result):
            result = await result

        return result or []

    except Exception as e:
        raise e



if st.button("بدء البحث الجمعي 🚀", type="primary"):

    if not query.strip():
        st.warning("رجاءً أدخل كلمة بحث أولاً.")

    else:
        st.info(f"جاري البحث عن: **{query}** ...")

        async def fetch_all():

            all_articles = []

            # إنشاء Query Object
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

                    results = await run_adapter(
                        adapter,
                        strategy
                    )

                    if results:
                        all_articles.extend(results)


                except Exception as e:
                    st.error(
                        f"خطأ في {source_name}: {str(e)}"
                    )


            return all_articles



        with st.spinner("جاري جلب الأبحاث..."):

            fetched_articles = asyncio.run(
                fetch_all()
            )


        if fetched_articles:

            st.success(
                f"تم العثور على {len(fetched_articles)} بحث/دراسة."
            )


            for i, article in enumerate(
                fetched_articles,
                1
            ):

                title = getattr(
                    article,
                    "title",
                    "بدون عنوان"
                )

                abstract = getattr(
                    article,
                    "abstract",
                    "لا يوجد ملخص متوفر."
                )

                doi = getattr(
                    article,
                    "doi",
                    "N/A"
                )


                with st.expander(
                    f"{i}. {title}"
                ):

                    st.write(
                        f"**DOI:** {doi}"
                    )

                    st.write(
                        f"**الملخص:** {abstract}"
                    )


        else:

            st.warning(
                "لم يتم العثور على نتائج تطابق هذا البحث."
            )
