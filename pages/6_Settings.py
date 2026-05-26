"""
pages/6_Settings.py — User filter settings for Sports Picks Grid.

All settings are persisted in st.session_state["settings"] and applied
on every picks page via utils.formatter.apply_settings().
"""
import copy
import streamlit as st
from utils.formatter import DEFAULT_SETTINGS, SPORT_EMOJI, TIER_ORDER

# ── Initialize session_state ──────────────────────────────────────────────
if "settings" not in st.session_state:
    st.session_state["settings"] = copy.deepcopy(DEFAULT_SETTINGS)

# Initialize per-widget keys from current settings (only on first visit).
# We use "sw_" prefix to avoid collisions with other session state keys.
_s = st.session_state["settings"]
_max = _s.get("max_picks", DEFAULT_SETTINGS["max_picks"])

if "sw_min_confidence" not in st.session_state:
    st.session_state["sw_min_confidence"] = int(_s.get("min_confidence", 0.0) * 100)
if "sw_min_edge" not in st.session_state:
    st.session_state["sw_min_edge"] = int(_s.get("min_edge", 0.0) * 100)
if "sw_tiers" not in st.session_state:
    st.session_state["sw_tiers"] = _s.get("tiers", DEFAULT_SETTINGS["tiers"])
for _sport in SPORT_EMOJI:
    _key = f"sw_max_{_sport}"
    if _key not in st.session_state:
        _default = DEFAULT_SETTINGS["max_picks"].get(_sport, DEFAULT_SETTINGS["max_picks"]["__default__"])
        st.session_state[_key] = _max.get(_sport, _default)

# ── Page header ───────────────────────────────────────────────────────────
st.header("⚙️ Filter Settings")
st.caption(
    "Adjust these settings to control which picks appear across all pages. "
    "Changes take effect immediately."
)

# ── Global Filters ────────────────────────────────────────────────────────
st.subheader("Global Filters")
col1, col2 = st.columns(2)

with col1:
    st.slider(
        "Minimum Confidence",
        min_value=0, max_value=95, step=5, format="%d%%",
        key="sw_min_confidence",
        help="Hide picks where the model's win probability is below this level.",
    )

with col2:
    st.slider(
        "Minimum Edge",
        min_value=0, max_value=20, step=1, format="%d%%",
        key="sw_min_edge",
        help="Hide picks where the edge over implied odds is below this level.",
    )

st.multiselect(
    "Tiers to Include",
    options=TIER_ORDER,
    key="sw_tiers",
    help="Only show picks that belong to the selected confidence tiers.",
)

st.divider()

# ── Per-Sport Pick Limits ─────────────────────────────────────────────────
st.subheader("Max Picks Per Sport")
st.caption(
    "High-volume sports (Table Tennis, Cricket, Darts, Tennis) can generate "
    "hundreds of picks per day. Use these sliders to cap how many are shown "
    "per sport — always the highest-confidence picks first."
)

# Layout: 3 columns
sports_sorted = sorted(SPORT_EMOJI.keys())
col_a, col_b, col_c = st.columns(3)
_cols = [col_a, col_b, col_c]

for _i, _sport in enumerate(sports_sorted):
    with _cols[_i % 3]:
        st.slider(
            f"{SPORT_EMOJI.get(_sport, '🎯')} {_sport}",
            min_value=5, max_value=100, step=5,
            key=f"sw_max_{_sport}",
        )

st.divider()

# ── Commit to session_state ───────────────────────────────────────────────
# Read all widget values and write the unified settings dict.
# This runs on every page render so settings stay in sync with sliders.
_tiers = st.session_state.get("sw_tiers") or DEFAULT_SETTINGS["tiers"]

st.session_state["settings"] = {
    "min_confidence": st.session_state.get("sw_min_confidence", 0) / 100.0,
    "min_edge": st.session_state.get("sw_min_edge", 0) / 100.0,
    "tiers": _tiers,
    "max_picks": {
        "__default__": DEFAULT_SETTINGS["max_picks"]["__default__"],
        **{
            _sport: st.session_state.get(f"sw_max_{_sport}",
                DEFAULT_SETTINGS["max_picks"].get(_sport, DEFAULT_SETTINGS["max_picks"]["__default__"]))
            for _sport in SPORT_EMOJI
        },
    },
}

# ── Reset button ──────────────────────────────────────────────────────────
if st.button("↩️ Reset to Defaults", type="secondary"):
    # Clear all widget state keys so sliders re-initialize from defaults
    for _key in list(st.session_state.keys()):
        if _key.startswith("sw_"):
            del st.session_state[_key]
    st.session_state["settings"] = copy.deepcopy(DEFAULT_SETTINGS)
    st.rerun()

# ── Current settings summary ──────────────────────────────────────────────
with st.expander("Current settings (debug)", expanded=False):
    st.json(st.session_state["settings"])
