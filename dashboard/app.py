"""Streamlit UBI Risk Dashboard — dark theme. Run: streamlit run dashboard/app.py"""

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

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ─── Background ──────────────────────────────────────── */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
.main {
    background-color: #0f1117 !important;
}
.main .block-container {
    padding: 2rem 3rem 1rem 3rem;
    max-width: 1200px;
}

/* ─── Sidebar ─────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #1a1d2e !important;
    border-right: 1px solid #252838;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
    color: #c8ccd8 !important;
}
[data-testid="stSidebar"] h1 {
    color: white !important;
    font-size: 1.25rem !important;
}

/* ─── Cards ───────────────────────────────────────────── */
.card {
    background: #1a1d2e;
    border: 1px solid #252838;
    border-radius: 14px;
    padding: 24px 28px;
    height: 100%;
}

/* ─── Section labels ──────────────────────────────────── */
.section-label {
    color: #4FC3F7;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    margin: 0 0 12px 0;
}

/* ─── Tip card — left blue accent ─────────────────────── */
.tip-card {
    background: #1a1d2e;
    border: 1px solid #252838;
    border-left: 4px solid #4FC3F7;
    border-radius: 14px;
    padding: 22px 28px;
}

/* ─── Chart image rounding ────────────────────────────── */
[data-testid="stImage"] > img {
    border-radius: 14px;
}

/* ─── Subtle dividers ─────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid #252838 !important;
    margin: 28px 0 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
# Per-tier card colours (background, border/text accent)
CARD_THEME = {
    "Low Risk":    {"bg": "#0b1f14", "accent": "#27ae60"},
    "Medium Risk": {"bg": "#1f1505", "accent": "#e67e22"},
    "High Risk":   {"bg": "#1f0808", "accent": "#e74c3c"},
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

def next_level_message(
    risk_score: int, risk_label: str, days_safe: int, level: str
) -> str:
    """One-line description of what the driver needs to reach the next tier."""
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


def md_to_html_bold(text: str, color: str = "#4FC3F7") -> str:
    """Convert **markdown bold** to <strong> tags with an accent colour."""
    return re.sub(r"\*\*(.+?)\*\*", rf'<strong style="color:{color};">\1</strong>', text)


def behavior_chart(driver_row: pd.Series, fleet_avg: pd.Series) -> plt.Figure:
    """Five dark-themed mini bar charts: driver vs fleet average per feature."""
    BG     = "#1a1d2e"
    BORDER = "#2a2d3e"
    TEXT   = "#c8ccd8"
    ACCENT = "#4FC3F7"

    fig, axes = plt.subplots(1, len(FEAT_DISPLAY), figsize=(13, 3.8))
    fig.patch.set_facecolor(BG)

    for ax, feat in zip(axes, FEAT_DISPLAY):
        d_val = float(driver_row[feat])
        f_val = float(fleet_avg[feat])
        bar_color = "#e74c3c" if d_val > f_val else "#27ae60"

        ax.set_facecolor(BG)
        ax.bar(
            ["You", "Fleet"],
            [d_val, f_val],
            color=[bar_color, "#3a4060"],
            edgecolor=BORDER,
            linewidth=0.5,
            width=0.55,
        )
        ax.set_title(FEAT_LABELS[feat], fontsize=9, fontweight="bold",
                     color=ACCENT, pad=5)
        ax.tick_params(axis="x", labelsize=8,   colors=TEXT)
        ax.tick_params(axis="y", labelsize=7.5, colors=TEXT)
        ax.grid(axis="y", alpha=0.15, linewidth=0.5, color=TEXT)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)

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
                fontsize=8.5, fontweight="bold", color=TEXT,
            )

    legend_handles = [
        mpatches.Patch(color="#e74c3c", label="Above fleet avg"),
        mpatches.Patch(color="#27ae60", label="Below fleet avg"),
        mpatches.Patch(color="#3a4060", label="Fleet average"),
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
# 1 · HEADER — level badge + driver ID
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="card" style="text-align:center; padding:44px 32px;">
    <div style="font-size:5rem; line-height:1; margin-bottom:10px;">{level_emoji}</div>
    <div style="font-size:2.4rem; font-weight:900; color:white;
                letter-spacing:0.01em;">{level_name}</div>
    <div style="font-size:0.95rem; color:#4FC3F7; font-weight:700;
                letter-spacing:0.16em; margin-top:10px;
                text-transform:uppercase;">{driver_id}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# 2 · RISK SCORE — colored metric card + progress bar
# ═════════════════════════════════════════════════════════════════════════════
_, col_mid, _ = st.columns([1, 2, 1])
with col_mid:
    st.markdown(f"""
    <div style="background:{theme['bg']}; border:2px solid {theme['accent']};
                border-radius:16px; padding:40px 32px; text-align:center;">
        <p class="section-label" style="color:{theme['accent']};">Risk Score</p>
        <div style="font-size:6rem; font-weight:900; color:{theme['accent']};
                    line-height:0.95;">{risk_score}</div>
        <div style="font-size:1.6rem; color:#3a3d4e; margin-top:2px;">/ 100</div>
        <div style="font-size:1.15rem; font-weight:700; color:{theme['accent']};
                    margin-top:14px;">{risk_label_full}</div>
        <div style="background:#0a0c14; border-radius:8px; height:12px;
                    margin:20px 0 0 0; overflow:hidden;">
            <div style="background:{theme['accent']}; width:{risk_score}%;
                        height:100%; border-radius:8px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# 3 · DRIVING BEHAVIOR — dark-themed 5-panel chart
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<p class="section-label">Driving Behavior vs. Fleet Average</p>',
            unsafe_allow_html=True)
fig = behavior_chart(driver_row, fleet_avg)
st.pyplot(fig, use_container_width=True)
plt.close(fig)

st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# 4 · STREAK & GAMIFICATION — two cards side by side
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<p class="section-label">Streak &amp; Gamification</p>',
            unsafe_allow_html=True)

col_streak, col_level = st.columns(2)

with col_streak:
    st.markdown(f"""
    <div class="card">
        <p class="section-label">🔥 Driving Streak</p>
        <p style="font-size:1.1rem; margin:0; color:white;
                  font-weight:500; line-height:1.5;">{streak_message}</p>
    </div>
    """, unsafe_allow_html=True)

with col_level:
    progress_html = md_to_html_bold(progress_msg)
    icon = "💎" if "Diamond" in driver_level else "🎯"
    st.markdown(f"""
    <div class="card">
        <p class="section-label">{icon} Level Progress</p>
        <p style="font-size:0.98rem; margin:0; color:#c8ccd8;
                  line-height:1.65;">{progress_html}</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# 5 · PERSONALIZED TIP — blue-accent card
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="tip-card">
    <p class="section-label" style="color:#4FC3F7;">💡 Personalized Tip</p>
    <p style="font-size:1rem; margin:0; color:#e0e0e0; line-height:1.7;">{tip}</p>
</div>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="text-align:center; padding:52px 0 16px 0;
            color:#2e3248; font-size:0.8rem; letter-spacing:0.03em;">
    Built by Camila Rojas &nbsp;•&nbsp;
    Inspired by a conversation with Intact's data science team &nbsp;•&nbsp;
    Synthetic data only
</div>
""", unsafe_allow_html=True)
