"""Streamlit UBI Risk Dashboard — run from project root: streamlit run dashboard/app.py"""

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

# ── Constants ─────────────────────────────────────────────────────────────────
SCORE_COLORS = {
    "Low Risk":    "#27ae60",
    "Medium Risk": "#e67e22",
    "High Risk":   "#e74c3c",
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
    """Describe what the driver needs to reach the next gamification tier."""
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

    # Bronze
    days_to_go = max(0, 31 - days_safe)
    parts = [f"**{days_to_go} more safe days**"] if days_to_go else []
    if risk_label == "High Risk":
        parts.append("a **lower risk score**")
    need = " and ".join(parts) or "keep maintaining your streak"
    return f"You are 🥉 Bronze — {need} away from 🥈 Silver"


def behavior_chart(driver_row: pd.Series, fleet_avg: pd.Series) -> plt.Figure:
    """One mini bar chart per feature: driver (coloured) vs fleet average (grey)."""
    fig, axes = plt.subplots(1, len(FEAT_DISPLAY), figsize=(13, 3.8))
    fig.patch.set_facecolor("white")

    for ax, feat in zip(axes, FEAT_DISPLAY):
        d_val = float(driver_row[feat])
        f_val = float(fleet_avg[feat])
        bar_color = "#e74c3c" if d_val > f_val else "#27ae60"

        ax.bar(
            ["You", "Fleet"],
            [d_val, f_val],
            color=[bar_color, "#95a5a6"],
            edgecolor="white",
            linewidth=0.8,
            width=0.55,
        )
        ax.set_title(FEAT_LABELS[feat], fontsize=9, fontweight="bold", pad=5)
        ax.tick_params(axis="x", labelsize=8)
        ax.tick_params(axis="y", labelsize=7.5)
        ax.grid(axis="y", alpha=0.22, linewidth=0.5)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)

        y_max = max(d_val, f_val, 0.1)
        for bar in ax.patches:
            h = bar.get_height()
            lbl = f"{h:.0f}" if feat in ("harsh_braking_count", "trips_recorded") else f"{h:.1f}"
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + y_max * 0.04,
                lbl,
                ha="center", va="bottom", fontsize=8.5, fontweight="bold",
            )

    legend_handles = [
        mpatches.Patch(color="#e74c3c", label="Above fleet avg"),
        mpatches.Patch(color="#27ae60", label="Below fleet avg"),
        mpatches.Patch(color="#95a5a6", label="Fleet average"),
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=3,
        fontsize=8.5,
        bbox_to_anchor=(0.5, -0.06),
        frameon=False,
    )
    plt.tight_layout(rect=[0, 0.1, 1, 1])
    return fig


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "features.csv")


df = load_data()
fleet_avg = df[FEAT_DISPLAY].mean()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🚗 UBI Dashboard")
    st.caption("Usage-Based Insurance · Driver Risk Scorer")
    st.divider()

    driver_id = st.selectbox(
        "Select Driver",
        options=df["customer_id"].tolist(),
    )
    days_safe = st.slider(
        "Days Safe",
        min_value=0,
        max_value=120,
        value=15,
        help="Consecutive days without harsh braking or high-speed events",
    )
    st.divider()
    st.caption(f"📊 Fleet size: **{len(df)} drivers**")

# ── Score the selected driver ─────────────────────────────────────────────────
driver_row = df[df["customer_id"] == driver_id].iloc[0]
result = score_driver(driver_row[FEAT_COLS].to_dict(), days_safe)

risk_score      = result["risk_score"]
risk_label_full = result["risk_label"]               # e.g. "🟢 Low Risk"
risk_label      = risk_label_full.split(" ", 1)[1]   # strip leading emoji
driver_level    = result["driver_level"]
streak_message  = result["streak_message"]
tip             = result["tip"]
score_color     = SCORE_COLORS[risk_label]

# ═════════════════════════════════════════════════════════════════════════════
# 1 · HEADER
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"""
    <div style="text-align:center; padding:28px 0 6px 0;">
        <div style="font-size:3.8rem; line-height:1.1;">{driver_level}</div>
        <div style="font-size:1.7rem; color:#555; font-weight:700;
                    margin-top:6px; letter-spacing:0.04em;">{driver_id}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# 2 · RISK SCORE
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Risk Score")

_, col_center, _ = st.columns([1, 2, 1])
with col_center:
    st.markdown(
        f"""
        <div style="text-align:center; padding:10px 0 4px 0;">
            <span style="font-size:5.5rem; font-weight:900; color:{score_color};
                         line-height:1;">{risk_score}</span>
            <span style="font-size:2.2rem; color:#bbb;"> / 100</span>
            <p style="font-size:1.25rem; font-weight:700; color:{score_color};
                      margin-top:4px;">{risk_label_full}</p>
        </div>
        <div style="background:#e0e0e0; border-radius:8px; height:18px;
                    margin:4px 0 14px 0; overflow:hidden;">
            <div style="background:{score_color}; width:{risk_score}%; height:100%;
                        border-radius:8px; transition:width 0.4s ease;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# 3 · DRIVING BEHAVIOR
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Driving Behavior vs. Fleet Average")
fig = behavior_chart(driver_row, fleet_avg)
st.pyplot(fig, use_container_width=True)
plt.close(fig)

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# 4 · STREAK & GAMIFICATION
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Streak & Gamification")

col_streak, col_level = st.columns(2)

with col_streak:
    st.markdown("**Driving Streak**")
    st.info(streak_message, icon="🔥")

with col_level:
    st.markdown("**Level Progress**")
    progress_msg = next_level_message(risk_score, risk_label, days_safe, driver_level)
    if "Diamond" in driver_level:
        st.success(progress_msg, icon="💎")
    else:
        st.warning(progress_msg, icon="🎯")

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# 5 · PERSONALIZED TIP
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Personalized Tip")
st.info(f"💡 {tip}")
