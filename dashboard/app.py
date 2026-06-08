"""Streamlit UBI Risk Dashboard — light minimalist theme. Run: streamlit run dashboard/app.py"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.scoring import score_driver

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UBI Risk Scorer",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ─── App background ──────────────────────────────── */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
.main {
    background-color: #F8F9FA !important;
}
.main .block-container {
    padding: 2rem 3rem 1rem 3rem;
    max-width: 1200px;
}

/* ─── Sidebar ─────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #E8E8E8;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: #555555 !important;
}
[data-testid="stSidebar"] h1 {
    color: #2D2D2D !important;
    font-size: 1.2rem !important;
}

/* ─── Dividers ────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid #E8E8E8 !important;
    margin: 24px 0 !important;
}

/* ─── Chart image rounding ────────────────────────── */
[data-testid="stImage"] > img {
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
CARD_THEME = {
    "Low Risk":    {"bg": "#D4EDD9", "text": "#2d6e44", "bar": "#5a9e72"},
    "Medium Risk": {"bg": "#FDF3CC", "text": "#7a5c10", "bar": "#c9971e"},
    "High Risk":   {"bg": "#FAD8D8", "text": "#a83228", "bar": "#d94f45"},
}

FEAT_DISPLAY = [
    "avg_speed",
    "max_speed",
    "harsh_braking_count",
    "recklessness_score",
    "trips_recorded",
]
FEAT_LABELS = {
    "avg_speed":           "Avg Speed\n(km/h)",
    "max_speed":           "Max Speed\n(km/h)",
    "harsh_braking_count": "Harsh\nBraking",
    "recklessness_score":  "Recklessness\n(°)",
    "trips_recorded":      "Trips\nRecorded",
}
FEAT_COLS = FEAT_DISPLAY + ["num_claims"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def card(body: str, *, extra_style: str = "") -> str:
    """Reusable white rounded card with light border and box shadow."""
    return (
        f'<div style="background:white; border:1px solid #E8E8E8; border-radius:12px;'
        f' padding:24px 28px; box-shadow:0 1px 6px rgba(0,0,0,0.05);'
        f' {extra_style}">{body}</div>'
    )


def section_label(text: str, color: str = "#7BAE8A") -> str:
    return (
        f'<p style="color:{color}; font-size:0.72rem; font-weight:700;'
        f' letter-spacing:0.15em; text-transform:uppercase; margin:0 0 12px 0;">'
        f"{text}</p>"
    )


def md_bold(text: str, color: str = "#8AAFC7") -> str:
    """Convert **markdown bold** → <strong> with accent colour."""
    return re.sub(r"\*\*(.+?)\*\*",
                  rf'<strong style="color:{color}; font-weight:700;">\1</strong>',
                  text)


def next_level_message(
    risk_score: int, risk_label: str, days_safe: int, level: str
) -> str:
    if "Diamond" in level:
        return "🏆 You've reached the top tier — keep up the excellent driving!"

    if "Gold" in level:
        days_to_go = max(0, 90 - days_safe)
        parts = [f"**{days_to_go} more safe days**"] if days_to_go else []
        if risk_score >= 20:
            parts.append("a **score below 20**")
        need = " and ".join(parts) or "keep maintaining your streak"
        return f"You are 🥇 Gold — {need} away from 💎 Diamond"

    if "Silver" in level:
        days_to_go = max(0, 61 - days_safe)
        parts = [f"**{days_to_go} more safe days**"] if days_to_go else []
        if risk_label != "Low Risk":
            parts.append("a **Low Risk** score")
        need = " and ".join(parts) or "keep maintaining your streak"
        return f"You are 🥈 Silver — {need} away from 🥇 Gold"

    days_to_go = max(0, 31 - days_safe)
    parts = [f"**{days_to_go} more safe days**"] if days_to_go else []
    if risk_label == "High Risk":
        parts.append("a **lower risk score**")
    need = " and ".join(parts) or "keep maintaining your streak"
    return f"You are 🥉 Bronze — {need} away from 🥈 Silver"


def behavior_chart(driver_row: pd.Series, fleet_avg: pd.Series) -> plt.Figure:
    """Clean minimal bar chart — sage green / dusty rose, no gridlines."""
    BG    = "#FAFAFA"
    ABOVE = "#E8A598"   # dusty rose — above average (worse)
    BELOW = "#7BAE8A"   # sage green — below average (better)
    FLEET = "#D5D8DC"   # light grey — fleet reference
    TEXT  = "#666666"
    TITLE = "#2D2D2D"

    fig, axes = plt.subplots(1, len(FEAT_DISPLAY), figsize=(13, 3.6))
    fig.patch.set_facecolor(BG)

    for ax, feat in zip(axes, FEAT_DISPLAY):
        d_val = float(driver_row[feat])
        f_val = float(fleet_avg[feat])
        bar_color = ABOVE if d_val > f_val else BELOW

        ax.set_facecolor(BG)
        ax.bar(
            ["You", "Fleet"],
            [d_val, f_val],
            color=[bar_color, FLEET],
            edgecolor="none",
            width=0.52,
        )
        # Rounded bar tops via a thin matching rect — skip, keep it clean
        ax.set_title(FEAT_LABELS[feat], fontsize=9, fontweight="600",
                     color=TITLE, pad=6)
        ax.tick_params(axis="x", labelsize=8, colors=TEXT, length=0)
        ax.tick_params(axis="y", labelsize=7.5, colors=TEXT, length=0)
        ax.set_axisbelow(True)
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_visible(False)

        y_max = max(d_val, f_val, 0.1)
        for bar in ax.patches:
            h = bar.get_height()
            lbl = (f"{h:.0f}"
                   if feat in ("harsh_braking_count", "trips_recorded")
                   else f"{h:.1f}")
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + y_max * 0.04,
                lbl,
                ha="center", va="bottom",
                fontsize=8.5, fontweight="600", color=TEXT,
            )

    legend_handles = [
        mpatches.Patch(color=ABOVE, label="Above fleet avg"),
        mpatches.Patch(color=BELOW, label="Below fleet avg"),
        mpatches.Patch(color=FLEET, label="Fleet average"),
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center", ncol=3,
        fontsize=8.5, bbox_to_anchor=(0.5, -0.06),
        frameon=False, labelcolor=TEXT,
    )
    plt.tight_layout(rect=[0, 0.1, 1, 1])
    return fig

# ── Data ──────────────────────────────────────────────────────────────────────

@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "features.csv")

df        = load_data()
fleet_avg = df[FEAT_DISPLAY].mean()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🚗 UBI Risk Scorer")
    st.caption("Usage-Based Insurance · Driver Risk Scorer")
    st.divider()
    driver_id = st.selectbox("Select Driver", df["customer_id"].tolist())
    days_safe = st.slider(
        "Days Safe", min_value=0, max_value=120, value=15,
        help="Consecutive days without harsh braking or high-speed events",
    )
    st.divider()
    st.caption(f"📊 Fleet size: **{len(df)} drivers**")

# ── Score ─────────────────────────────────────────────────────────────────────
driver_row      = df[df["customer_id"] == driver_id].iloc[0]
result          = score_driver(driver_row[FEAT_COLS].to_dict(), days_safe)

risk_score      = result["risk_score"]
risk_label_full = result["risk_label"]
risk_label      = risk_label_full.split(" ", 1)[1]
driver_level    = result["driver_level"]
streak_message  = result["streak_message"]
tip             = result["tip"]

theme           = CARD_THEME[risk_label]
level_emoji, level_name = driver_level.split(" ", 1)
progress_msg    = next_level_message(risk_score, risk_label, days_safe, driver_level)

# ═════════════════════════════════════════════════════════════════════════════
# 1 · HEADER — level badge
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(card(f"""
    <div style="text-align:center; padding:32px 0 24px 0;">
        <div style="font-size:4.5rem; line-height:1; margin-bottom:12px;">{level_emoji}</div>
        <div style="font-size:1.8rem; font-weight:600; color:#888888;
                    letter-spacing:0.01em;">{level_name}</div>
        <div style="font-size:0.85rem; color:#8AAFC7; font-weight:600;
                    letter-spacing:0.16em; margin-top:10px;
                    text-transform:uppercase;">{driver_id}</div>
    </div>
"""), unsafe_allow_html=True)

st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# 2 · RISK SCORE
# ═════════════════════════════════════════════════════════════════════════════
_, col_mid, _ = st.columns([1, 2, 1])
with col_mid:
    st.markdown(f"""
    <div style="background:{theme['bg']}; border-radius:16px;
                padding:40px 32px; text-align:center;
                box-shadow:0 1px 6px rgba(0,0,0,0.05);">
        {section_label("Risk Score", color=theme['text'])}
        <div style="font-size:6rem; font-weight:900; color:{theme['text']};
                    line-height:0.95;">{risk_score}</div>
        <div style="font-size:1.5rem; color:{theme['text']}; opacity:0.45;
                    margin-top:2px;">/ 100</div>
        <div style="font-size:1.1rem; font-weight:600; color:{theme['text']};
                    margin-top:14px;">{risk_label_full}</div>
        <div style="background:rgba(0,0,0,0.08); border-radius:6px; height:8px;
                    margin:18px 0 0 0; overflow:hidden;">
            <div style="background:{theme['bar']}; width:{risk_score}%;
                        height:100%; border-radius:6px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# 3 · DRIVING BEHAVIOR
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(section_label("Driving Behavior vs. Fleet Average"), unsafe_allow_html=True)
fig = behavior_chart(driver_row, fleet_avg)
st.pyplot(fig, use_container_width=True)
plt.close(fig)

st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# 4 · STREAK & GAMIFICATION
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(section_label("Streak &amp; Gamification"), unsafe_allow_html=True)

col_streak, col_level = st.columns(2)

with col_streak:
    st.markdown(card(f"""
        {section_label("🔥 Driving Streak")}
        <p style="font-size:1.05rem; margin:0; color:#2D2D2D;
                  font-weight:500; line-height:1.6;">{streak_message}</p>
    """), unsafe_allow_html=True)

with col_level:
    icon = "💎" if "Diamond" in driver_level else "🎯"
    progress_html = md_bold(progress_msg, color="#8AAFC7")
    st.markdown(card(f"""
        {section_label(f"{icon} Level Progress")}
        <p style="font-size:0.97rem; margin:0; color:#555555;
                  line-height:1.7;">{progress_html}</p>
    """), unsafe_allow_html=True)

st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# 5 · PERSONALIZED TIP — soft lavender card
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="background:#EDE8F5; border-radius:12px; padding:24px 28px;
            box-shadow:0 1px 6px rgba(0,0,0,0.04);">
    {section_label("💡 Personalized Tip", color="#7B6CA0")}
    <p style="font-size:1rem; margin:0; color:#3d3050; line-height:1.75;">{tip}</p>
</div>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="text-align:center; padding:52px 0 16px 0;
            color:#BBBBBB; font-size:0.78rem; letter-spacing:0.03em;">
    Built by Camila Rojas &nbsp;•&nbsp;
    Inspired by a conversation with Intact's data science team &nbsp;•&nbsp;
    Synthetic data only
</div>
""", unsafe_allow_html=True)
