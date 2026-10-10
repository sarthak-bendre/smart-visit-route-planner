"""Create the sample dataset: 22 fictional dealers spread across Pune.

Run from the project root:  python data/generate_dealers.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
OUT = Path(__file__).resolve().parent / "dealers.csv"

# (area, approx. latitude, approx. longitude)
AREAS = [
    ("Kothrud", 18.5074, 73.8077),
    ("Baner", 18.5590, 73.7868),
    ("Hinjewadi", 18.5913, 73.7389),
    ("Hadapsar", 18.5089, 73.9260),
    ("Viman Nagar", 18.5679, 73.9143),
    ("Aundh", 18.5580, 73.8075),
    ("Wakad", 18.5975, 73.7700),
    ("Kharadi", 18.5515, 73.9348),
    ("Kondhwa", 18.4655, 73.8920),
    ("Katraj", 18.4575, 73.8677),
    ("Pimpri", 18.6279, 73.8009),
    ("Swargate", 18.5018, 73.8636),
    ("Deccan", 18.5167, 73.8415),
    ("Camp", 18.5150, 73.8780),
    ("Yerawada", 18.5523, 73.8862),
    ("Warje", 18.4851, 73.7997),
    ("Sinhagad Road", 18.4800, 73.8270),
    ("Bibwewadi", 18.4700, 73.8640),
    ("Wanowrie", 18.4900, 73.9000),
    ("Pashan", 18.5380, 73.7900),
    ("Kalyani Nagar", 18.5480, 73.9020),
    ("Bavdhan", 18.5150, 73.7800),
]

CATEGORIES = {
    "Electronics": ["Digital Hub", "Electro World", "Smart Electronics", "Vision Electronics"],
    "Mobile": ["Mobile Point", "Phone Planet", "Cell Zone", "Mobile Gallery"],
    "Appliance": ["Home Appliances", "Kitchen Kraft", "Cool Home Store", "Appliance Mart"],
    "Two-Wheeler": ["Motors", "Auto Wheels", "Bike Point", "Two Wheels"],
}
PREFIXES = ["Shree", "Sai", "Om", "Ganesh", "Laxmi", "Royal", "Prime", "New", "Star", "Shiv", "Jai"]

# Typical monthly disbursal targets (Rs lakh) by dealer category.
TARGET_RANGE = {
    "Electronics": (15, 45),
    "Mobile": (8, 25),
    "Appliance": (10, 35),
    "Two-Wheeler": (25, 60),
}


def generate(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for i, (area, lat, lon) in enumerate(AREAS, start=1):
        category = rng.choice(list(CATEGORIES))
        name = f"{rng.choice(PREFIXES)} {rng.choice(CATEGORIES[category])}"
        lo, hi = TARGET_RANGE[category]
        target = float(rng.integers(lo, hi + 1))
        # Most dealers are behind target mid-month; a few are ahead.
        achieved = round(target * float(rng.uniform(0.45, 1.2)), 1)
        rows.append(
            {
                "dealer_id": f"D{i:03d}",
                "dealer_name": name,
                "area": area,
                "category": category,
                # Small jitter so dealers are not exactly on the area centroid.
                "latitude": round(lat + float(rng.normal(0, 0.003)), 6),
                "longitude": round(lon + float(rng.normal(0, 0.003)), 6),
                "monthly_target_lakh": target,
                "achieved_lakh": achieved,
                "pending_issues": int(rng.choice([0, 0, 0, 0, 0, 1, 1, 2, 3, 5])),
                "days_since_last_visit": int(rng.choice([2, 3, 5, 7, 9, 12, 14, 18, 21, 28, 35])),
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate()
    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df)} dealers to {OUT}")
