"""
Generates 24 months of realistic synthetic supply chain KPI data.

Run: python data/seeds/generate_kpis.py

Design choices for the synthetic data:
- Each KPI follows a base trend + seasonal component + noise (classic additive model)
- 3 anomaly windows are injected deterministically so demos are reproducible
- Supplier breakdown is generated for DPPM and OTIF (5 suppliers each)
- All values are clipped to physically plausible ranges
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Allow running as a script from the project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kpi_lens.config import settings
from kpi_lens.db.schema import Base, KPIRecord
from kpi_lens.kpis.definitions import ALL_KPIS, KPIDefinition
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

SEED = 42
N_WEEKS = 104  # 2 years of weekly data
rng = np.random.default_rng(SEED)

# Anomaly windows: (start_week_offset, duration_weeks, kpi_name, direction)
INJECTED_ANOMALIES = [
    (30, 3, "supplier_dppm", "spike"),   # Supplier quality event
    (60, 5, "otif", "drop"),             # Logistics disruption
    (85, 4, "dio", "spike"),             # Inventory build-up
]


def generate_series(
    kpi: KPIDefinition,
    n_weeks: int,
    noise_pct: float = 0.03,
) -> list[float]:
    """
    Generate a weekly time series for a KPI using an additive model:
        value = base + seasonal + trend + noise

    The base is set to the green threshold so the series is healthy by default.
    Anomalies are injected separately via inject_anomalies().
    """
    base = kpi.green_threshold
    # Gentle directional trend: ±0.5% per week over the full series
    trend = np.linspace(0, base * 0.05, n_weeks) * rng.choice([-1, 1])
    # Annual seasonality (52-week period) with amplitude = 3% of base
    seasonality = base * 0.03 * np.sin(2 * np.pi * np.arange(n_weeks) / 52)
    noise = rng.normal(0, base * noise_pct, n_weeks)
    values = base + trend + seasonality + noise
    # Clip to plausible range (KPI can't be negative or above 100% for rates)
    if kpi.unit == "%":
        values = np.clip(values, 0, 100)
    elif kpi.direction == "lower_is_better":
        values = np.clip(values, 0, kpi.red_threshold * 2)
    return values.tolist()


def inject_anomalies(
    series: list[float],
    kpi_name: str,
    kpi: KPIDefinition,
) -> list[float]:
    s = list(series)
    for start, duration, target_kpi, direction in INJECTED_ANOMALIES:
        if target_kpi != kpi_name:
            continue
        for w in range(start, min(start + duration, len(s))):
            if direction == "spike":
                # Push to red territory
                s[w] = kpi.red_threshold * (1.5 if kpi.direction == "lower_is_better" else 0.6)
            else:
                s[w] = kpi.red_threshold * (0.7 if kpi.direction == "higher_is_better" else 1.5)
    return s


def main() -> None:
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)

    start_date = date.today() - timedelta(weeks=N_WEEKS)
    records: list[KPIRecord] = []

    for kpi in ALL_KPIS:
        series = generate_series(kpi, N_WEEKS)
        series = inject_anomalies(series, kpi.name, kpi)

        for week_idx, value in enumerate(series):
            period_start = start_date + timedelta(weeks=week_idx)
            period_end = period_start + timedelta(days=6)
            records.append(
                KPIRecord(
                    kpi_name=kpi.name,
                    period_start=period_start,
                    period_end=period_end,
                    value=round(value, 3),
                    unit=kpi.unit,
                    entity="global",
                    source="synthetic_seed",
                )
            )

    with Session(engine) as session:
        # Clear existing seed data before re-seeding
        session.query(KPIRecord).filter(KPIRecord.source == "synthetic_seed").delete()
        session.bulk_save_objects(records)
        session.commit()

    print(f"✅ Seeded {len(records)} KPI records ({N_WEEKS} weeks × {len(ALL_KPIS)} KPIs)")
    print(f"   Database: {settings.database_url}")


if __name__ == "__main__":
    main()
