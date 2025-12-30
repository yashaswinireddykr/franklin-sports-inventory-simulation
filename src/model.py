from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import numpy as np
import pandas as pd


@dataclass
class SimParams:
    horizon_weeks: int
    lead_time_weeks: int
    review_period_weeks: int
    service_level: float          # 0.80 to 0.99
    safety_factor: float          # 0.0 to 3.0
    num_sims: int


def _z_from_service_level(sl: float) -> float:
    """Approx z for common service levels (good enough for portfolio demo)."""
    # You can replace with scipy.stats.norm.ppf later if you want.
    table = {
        0.80: 0.842, 0.85: 1.036, 0.90: 1.282, 0.95: 1.645, 0.97: 1.881, 0.98: 2.054, 0.99: 2.326
    }
    # snap to nearest key
    key = min(table.keys(), key=lambda k: abs(k - sl))
    return table[key]


def _pick_demand_col(df_asin: pd.DataFrame) -> str:
    """Pick the demand/forecast column from your masked dataset."""
    for c in ["forecast", "forecast_qty", "pred_demand", "demand_forecast", "units_forecast"]:
        if c in df_asin.columns:
            return c
    raise ValueError("No forecast/demand column found. Expected a column like 'forecast'.")


def simulate_inventory_po(df_asin: pd.DataFrame, params: SimParams) -> Dict[str, Any]:
    """
    NDA-safe simulation:
    - Uses masked weekly forecast as expected demand
    - Adds uncertainty via Poisson-ish noise
    - Periodic review policy (order-up-to)
    Outputs:
      recommended_po_qty, weeks_of_cover, stockout_risk, sim_table (avg path)
    """
    df_asin = df_asin.copy()

    # Sort time if date exists
    if "start_date_pred" in df_asin.columns:
        df_asin["start_date_pred"] = pd.to_datetime(df_asin["start_date_pred"], errors="coerce")
        df_asin = df_asin.sort_values("start_date_pred")

    demand_col = _pick_demand_col(df_asin)

    # Take horizon demand series (fallback: use whatever rows we have)
    demand_series = df_asin[demand_col].dropna().astype(float).values
    if len(demand_series) == 0:
        raise ValueError("Demand/forecast column exists, but has no usable values.")

    horizon = params.horizon_weeks
    if len(demand_series) < horizon:
        # pad by repeating last known forecast (safe demo behavior)
        demand_series = np.pad(demand_series, (0, horizon - len(demand_series)), mode="edge")
    else:
        demand_series = demand_series[:horizon]

    # Initial inventory
    if "onhand_units" in df_asin.columns and pd.notna(df_asin["onhand_units"].iloc[0]):
        initial_onhand = float(df_asin["onhand_units"].iloc[0])
    else:
        initial_onhand = float(max(0, np.nanmedian(demand_series) * 4))  # safe fallback

    # Safety stock & ordering logic
    z = _z_from_service_level(params.service_level)
    lead = params.lead_time_weeks
    review = params.review_period_weeks

    # Expected demand over lead and review windows
    mean_weekly = float(np.mean(demand_series))
    # uncertainty: scale variance by safety_factor; use Poisson-like sd ~ sqrt(mean)
    base_sd_weekly = float(np.sqrt(max(mean_weekly, 1.0)))
    sd_weekly = base_sd_weekly * (1.0 + params.safety_factor)

    def mean_over(weeks: int) -> float:
        return float(np.sum(demand_series[:weeks])) if weeks <= horizon else float(np.sum(demand_series))

    mean_lead = mean_over(min(lead, horizon))
    mean_lead_review = mean_over(min(lead + review, horizon))

    sd_lead = np.sqrt(max(lead, 1)) * sd_weekly
    sd_lead_review = np.sqrt(max(lead + review, 1)) * sd_weekly

    # Order-up-to level (periodic review)
    order_up_to = mean_lead_review + z * sd_lead_review

    # --- Monte Carlo simulation ---
    num_sims = params.num_sims
    inv_paths = np.zeros((num_sims, horizon))
    stockout_flags = np.zeros(num_sims, dtype=int)
    first_order_qtys = []

    rng = np.random.default_rng(42)

    for s in range(num_sims):
        onhand = initial_onhand
        pipeline = {}  # arrival_week -> qty

        first_order_qty = 0.0

        for t in range(horizon):
            # Receive orders
            if t in pipeline:
                onhand += pipeline[t]

            # Realized demand (non-negative)
            lam = max(demand_series[t], 0.0)
            # Poisson demand around forecast (NDA-safe, interpretable)
            demand = float(rng.poisson(lam=max(lam, 0.0)))

            onhand -= demand
            if onhand < 0:
                stockout_flags[s] = 1
                onhand = 0.0

            # Review: place order at t=0 and every 'review' weeks
            if t % review == 0:
                # Inventory position = onhand + pipeline on order (not yet received)
                inv_position = onhand + sum(pipeline.values())
                qty = max(0.0, order_up_to - inv_position)

                arrival_week = t + lead
                if qty > 0 and arrival_week < horizon:
                    pipeline[arrival_week] = pipeline.get(arrival_week, 0.0) + qty

                if t == 0:
                    first_order_qty = qty

            inv_paths[s, t] = onhand

        first_order_qtys.append(first_order_qty)

    avg_path = inv_paths.mean(axis=0)
    stockout_risk = float(stockout_flags.mean())

    # Weeks of cover: current onhand / avg weekly demand
    weeks_of_cover = float(initial_onhand / max(mean_weekly, 1.0))

    recommended_po_qty = float(np.median(first_order_qtys))

    sim_table = pd.DataFrame({
        "week": np.arange(1, horizon + 1),
        "avg_onhand": avg_path,
        "forecast_demand": demand_series
    })

    return {
        "recommended_po_qty": recommended_po_qty,
        "weeks_of_cover": weeks_of_cover,
        "stockout_risk": stockout_risk,
        "sim_table": sim_table
    }
