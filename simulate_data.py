"""
Generates synthetic UBI telematics and claims data for 50 drivers around Montreal.

Driver profiles:
  DRV_001–DRV_015  →  risky  (high speed, erratic steering, frequent claims)
  DRV_016–DRV_040  →  safe   (moderate speed, smooth steering, rare claims)
  DRV_041–DRV_050  →  medium (in-between)
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

SEED = 42
np.random.seed(SEED)

NUM_DRIVERS = 50
TRIPS_PER_DRIVER = 10
TRIP_SECONDS = 300  # ~5 minutes

# Montreal city center
BASE_LAT = 45.5017
BASE_LON = -73.5673

# Degree-to-meter conversions at Montreal latitude
METERS_PER_DEG_LAT = 111_000
METERS_PER_DEG_LON = 111_000 * np.cos(np.radians(BASE_LAT))  # ≈ 78_600

PROFILE_PARAMS = {
    "risky": {
        "speed_mean": 16.0,   # m/s ≈ 58 km/h average
        "speed_std": 6.0,
        "speed_max": 38.0,    # ≈ 137 km/h
        "heading_noise": 0.30, # rad/s — abrupt lane changes / weaving
        "claims_probs": [0.0, 0.25, 0.40, 0.35],  # 0–3 claims
        "responsible_p": 0.80,
        "total_loss_p": 0.35,
    },
    "safe": {
        "speed_mean": 7.5,    # m/s ≈ 27 km/h average
        "speed_std": 1.8,
        "speed_max": 14.0,    # ≈ 50 km/h
        "heading_noise": 0.04, # very smooth
        "claims_probs": [0.70, 0.28, 0.02, 0.00],
        "responsible_p": 0.15,
        "total_loss_p": 0.03,
    },
    "medium": {
        "speed_mean": 11.0,
        "speed_std": 3.5,
        "speed_max": 22.0,    # ≈ 79 km/h
        "heading_noise": 0.12,
        "claims_probs": [0.45, 0.35, 0.15, 0.05],
        "responsible_p": 0.45,
        "total_loss_p": 0.12,
    },
}


def driver_profile(driver_index: int) -> str:
    if driver_index < 15:
        return "risky"
    if driver_index < 40:
        return "safe"
    return "medium"


def simulate_trip(
    customer_id: str,
    profile: str,
    trip_start: datetime,
) -> list[dict]:
    p = PROFILE_PARAMS[profile]
    records = []

    # Random starting point within ~3 km of Montreal center
    lat = BASE_LAT + np.random.uniform(-0.027, 0.027)
    lon = BASE_LON + np.random.uniform(-0.038, 0.038)
    heading = np.random.uniform(0, 2 * np.pi)
    speed = max(0.0, np.random.normal(p["speed_mean"], p["speed_std"]))

    for sec in range(TRIP_SECONDS):
        records.append(
            {
                "customer_id": customer_id,
                "timestamp": (trip_start + timedelta(seconds=sec)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
            }
        )

        # Smooth speed update (auto-correlation keeps it realistic)
        speed += np.random.normal(0, p["speed_std"] * 0.25)
        speed = float(np.clip(speed, 0.0, p["speed_max"]))

        # Heading drift (risky = large random jumps; safe = gentle curve)
        heading += np.random.normal(0, p["heading_noise"])

        lat += (speed * np.cos(heading)) / METERS_PER_DEG_LAT
        lon += (speed * np.sin(heading)) / METERS_PER_DEG_LON

    return records


def simulate_claims(customer_id: str, profile: str) -> dict:
    p = PROFILE_PARAMS[profile]
    num_claims = int(np.random.choice([0, 1, 2, 3], p=p["claims_probs"]))

    # responsible / total_loss only meaningful when there are claims
    responsible = bool(np.random.random() < p["responsible_p"]) if num_claims > 0 else False
    total_loss = bool(np.random.random() < p["total_loss_p"]) if num_claims > 0 else False

    return {
        "customer_id": customer_id,
        "num_claims": num_claims,
        "responsible": responsible,
        "total_loss": total_loss,
    }


def main() -> None:
    os.makedirs("data", exist_ok=True)

    trip_rows: list[dict] = []
    claim_rows: list[dict] = []

    base_time = datetime(2024, 1, 1, 7, 30, 0)

    for i in range(NUM_DRIVERS):
        customer_id = f"DRV_{i + 1:03d}"
        profile = driver_profile(i)

        for t in range(TRIPS_PER_DRIVER):
            # Space trips: different day each trip, random hour between 7–19
            trip_hour = np.random.randint(7, 20)
            trip_start = base_time + timedelta(days=i * TRIPS_PER_DRIVER + t, hours=trip_hour - 7)
            trip_rows.extend(simulate_trip(customer_id, profile, trip_start))

        claim_rows.append(simulate_claims(customer_id, profile))

    trips_df = pd.DataFrame(trip_rows)
    claims_df = pd.DataFrame(claim_rows)

    trips_df.to_csv("data/trips.csv", index=False)
    claims_df.to_csv("data/claims.csv", index=False)

    print(f"trips.csv  → {len(trips_df):,} rows  ({NUM_DRIVERS} drivers × {TRIPS_PER_DRIVER} trips × {TRIP_SECONDS}s)")
    print(f"claims.csv → {len(claims_df)} rows")
    print()
    print("Profile breakdown:")
    for profile in ("risky", "safe", "medium"):
        subset = claims_df[claims_df["customer_id"].isin(
            [f"DRV_{i+1:03d}" for i in range(NUM_DRIVERS) if driver_profile(i) == profile]
        )]
        print(
            f"  {profile:6s}  n={len(subset):2d}  "
            f"avg_claims={subset['num_claims'].mean():.2f}  "
            f"responsible={subset['responsible'].mean():.0%}  "
            f"total_loss={subset['total_loss'].mean():.0%}"
        )


if __name__ == "__main__":
    main()
