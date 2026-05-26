"""
predictions.py — Sports Picks Grid entry point.

Run with:
    streamlit run predictions.py
"""
import streamlit as st

from utils.fetcher import load_all_bets, get_cache_age
from footer import add_betting_oracle_footer

st.set_page_config(
    page_title="Sports Picks Grid",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    from pathlib import Path
    logo = Path("data_files/logo.png")
    if logo.exists():
        st.image(str(logo), width=220)
    else:
        st.markdown("## 🎯 Sports Picks Grid")

    st.caption("Daily picks from all Betting Oracle models")
    st.divider()

    if st.button("🔄 Refresh picks", width='stretch'):
        st.cache_data.clear()
        if "all_bets_df" in st.session_state:
            del st.session_state["all_bets_df"]
        st.rerun()

    age = get_cache_age()
    if age:
        st.caption(f"Cache updated: {age}")

# ── Pre-warm data (loaded once; all pages read from session_state) ────────────
if "all_bets_df" not in st.session_state:
    with st.spinner("Loading picks from all sport models..."):
        st.session_state["all_bets_df"] = load_all_bets()

# ── Initialize user settings (defaults only; Settings page can override) ──────
if "settings" not in st.session_state:
    import copy
    from utils.formatter import DEFAULT_SETTINGS
    st.session_state["settings"] = copy.deepcopy(DEFAULT_SETTINGS)

# ── Navigation ────────────────────────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/1_Today.py",       title="Today's Picks",   icon="📅"),
    st.Page("pages/2_By_Sport.py",    title="By Sport",        icon="🏆"),
    st.Page("pages/3_Best_Bets.py",   title="Best Bets",       icon="🔥"),
    st.Page("pages/4_Performance.py", title="Performance",     icon="📊"),
    st.Page("pages/5_About.py",       title="About",           icon="ℹ️"),
    st.Page("pages/6_Settings.py",    title="Settings",        icon="⚙️"),
])

pg.run()
add_betting_oracle_footer()
