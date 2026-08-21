import streamlit as st
import asyncio
from adapters.pubmed import PubMedAdapter
from adapters.europe_pmc import EuropePMCAdapter
from adapters.openalex import OpenAlexAdapter
from literature.deduplication import Deduplicator

# إعدادات الصفحة والتصميم
st.set_page_config(
    page_title="Research Copilot",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 Research Copilot - المساعد البحثي الطبي")
st.markdown("مرحباً بك! يمكنك البحث في قواعد البيانات الطبية العالمية (PubMed, Europe PMC, OpenAlex) وتصفيات النتائج بسهولة.")

# القائمة الجانبية للخيارات
st.sidebar.header("إعدادات البحث")
selected_sources = st.sidebar.multiselect(
    "اختر المصادر البحثية:",
    ["PubMed", "Europe PMC", "OpenAlex"],
    default=["PubMed", "Europe PMC"]
)

max_results = st.sidebar.slider("عدد النتائج من كل مصدر:", min_value=5, max_value=50, value=10)

# مربع البحث الرئيسي
query = st.text_input("أدخل الكلمات المفتاحية للبحث الطبي (مثال: Diabetes treatment, Laparoscopic surgery):", "")

if st.button("بدء البحث الجمعي 🚀", type="primary"):
    if not query.strip():
        st.warning("رجاءً أدخل كلمة بحث أولاً.")
    else:
        st.info(f"جاري البحث عن: **{query}** ...")
        
        results = []
        
        # دالة البحث
        async def fetch_all():
            all_articles = []
            if "PubMed" in selected_sources:
                try:
                    pm_adapter = PubMedAdapter()
                    res = await pm_adapter.search(query, max_results=max_results)
                    all_articles.extend(res)
                except Exception as e:
                    st.error(f"خطأ أثناء البحث في PubMed: {e}")
            
            if "Europe PMC" in selected_sources:
                try:
                    epmc_adapter = EuropePMCAdapter()
                    res = await epmc_adapter.search(query, max_results=max_results)
                    all_articles.extend(res)
                except Exception as e:
                    st.error(f"خطأ أثناء البحث في Europe PMC: {e}")

            if "OpenAlex" in selected_sources:
                try:
                    alex_adapter = OpenAlexAdapter()
                    res = await alex_adapter.search(query, max_results=max_results)
                    all_articles.extend(res)
                except Exception as e:
                    st.error(f"خطأ أثناء البحث في OpenAlex: {e}")

            return all_articles

        # تشغيل البحث
        with st.spinner("جاري جلب الأبحاث وتصفيتها..."):
            fetched_articles = asyncio.run(fetch_all())
            
            if fetched_articles:
                st.success(f"تم العثور على {len(fetched_articles)} بحث/دراسة.")
                
                # إظهار الأبحاث في بطاقات
                for i, article in enumerate(fetched_articles, 1):
                    title = getattr(article, 'title', 'بدون عنوان')
                    abstract = getattr(article, 'abstract', 'لا يوجد ملخص متوفر.')
                    doi = getattr(article, 'doi', 'N/A')
                    
                    with st.expander(f"{i}. {title}"):
                        st.write(f"**DOI:** {doi}")
                        st.write(f"**الملخص:** {abstract}")
            else:
                st.warning("لم يتم العثور على نتائج طابق هذا البحث.")
