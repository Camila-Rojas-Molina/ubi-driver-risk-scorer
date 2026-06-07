# UBI Driver Risk Scorer

A telematics-based driver risk scoring pipeline with gamification, built to explore usage-based insurance pricing concepts.

---

## Overview

Usage-based insurance (UBI) prices car insurance based on how a person actually drives, rather than demographic proxies. This project builds an end-to-end pipeline that simulates GPS trip data, engineers driving behavior features, trains a risk classifier, and surfaces the results in an interactive dashboard.

It was inspired by a conceptual discussion about telematics-driven pricing. All data is synthetic — generated from scratch using configurable driver profiles (safe, medium, risky). No real driver data, proprietary systems, or internal company information of any kind was used.

---

## Pipeline

```
simulate_data.py          →  Generates synthetic GPS trips + claims for 50 drivers
notebooks/01_feature_engineering.ipynb  →  Haversine speed, harsh braking, bearing-change recklessness score
notebooks/02_model_training.ipynb       →  Random Forest classifier + evaluation
src/scoring.py            →  Scores any driver: risk score, level, streak, tip
dashboard/app.py          →  Streamlit dashboard with fleet comparison
```

---

## Features

- **GPS feature engineering** — avg/max speed (haversine), harsh braking events, recklessness score (bearing change)
- **Random Forest classifier** — binary high-risk label, trained on telematics + claims features
- **Risk score 0–100** — derived from predicted probability, with 🟢 Low / 🟡 Medium / 🔴 High tiers
- **Driver level system** — 🥉 Bronze → 🥈 Silver → 🥇 Gold → 💎 Diamond, based on score and safe-driving streak
- **Streak tracker** — consecutive days without harsh braking or speeding
- **Personalized tips** — surfaces the driver's single worst behavior signal
- **Fleet comparison chart** — bar chart of driver vs. fleet average across all telematics features

---

## Tech Stack

| Purpose | Library |
|---|---|
| Data & features | `pandas`, `numpy`, `haversine` |
| Modeling | `scikit-learn`, `joblib` |
| Visualization | `matplotlib`, `seaborn` |
| Dashboard | `streamlit` |

---

## Live Demo

[**ubi-driver-risk-scorer.streamlit.app**](https://ubi-driver-risk-scorer-2s4jmbfbbu3zalqprsyfsa.streamlit.app/)

---

## Run Locally

```bash
git clone https://github.com/your-username/ubi-driver-risk-scorer.git
cd ubi-driver-risk-scorer
pip install -r requirements.txt
streamlit run dashboard/app.py
```

To regenerate the synthetic data and retrain the model:

```bash
python simulate_data.py
# then run the two notebooks in order
```

---

## Disclaimer

This project uses entirely synthetic data inspired by a conceptual discussion about telematics-based insurance pricing. No proprietary data, systems, or internal information from any company was used. This is a personal learning project built to explore the UBI problem space.
