import pandas as pd
import streamlit as st
from pathlib import Path
from src.model import SimParams, simulate_inventory_po
import numpy as np

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="Franklin Sports Inventory Simulation", layout="wide")

st.title("Franklin Sports — Inventory & PO Simulation (NDA-safe demo)")
st.caption("This app uses masked data only. No proprietary Franklin Sports data is included.")

# -------------------------
# Load data
# -------------------------
BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "masked_merged_sample.csv"

df = pd.read_csv(DATA_PATH)

# -------------------------
# Sidebar: product selection
# -------------------------
st.sidebar.header("1️⃣ Select product")

filtered_df = df.copy()

if "division" in df.columns:
    division = st.sidebar.selectbox(
        "Division", ["All"] + sorted(df["division"].dropna().unique().tolist())
    )
    if division != "All":
        filtered_df = filtered_df[filtered_df["division"] == division]

if "taxonomy" in df.columns:
    taxonomy = st.sidebar.selectbox(
        "Taxonomy", ["All"] + sorted(filtered_df["taxonomy"].dropna().unique().tolist())
    )
    if taxonomy != "All":
        filtered_df = filtered_df[filtered_df["taxonomy"] == taxonomy]

asin_list = sorted(filtered_df["asin"].dropna().unique().tolist())
selected_asin = st.sidebar.selectbox("ASIN", asin_list)

selected_row = filtered_df[filtered_df["asin"] == selected_asin].iloc[0]

# -------------------------
# Sidebar: simulation controls
# -------------------------
st.sidebar.divider()
st.sidebar.header("2️⃣ Simulation controls")

horizon_weeks = st.sidebar.slider("Forecast horizon (weeks)", 4, 52, 26, step=1)
lead_time_weeks = st.sidebar.slider("Lead time (weeks)", 1, 20, 8, step=1)
review_period_weeks = st.sidebar.slider("Review period (weeks)", 1, 8, 1, step=1)

service_level = st.sidebar.slider("Service level (%)", 80, 99, 95, step=1)
safety_factor = st.sidebar.slider("Safety stock factor (multiplier)", 0.0, 3.0, 1.0, step=0.1)

num_sims = st.sidebar.selectbox("Monte Carlo simulations", [100, 250, 500, 1000], index=1)

run = st.sidebar.button("▶ Run simulation", type="primary")

# -------------------------
# Main: product summary
# -------------------------
st.subheader("Selected Product")

col1, col2, col3, col4 = st.columns(4)
col1.metric("ASIN", selected_row.get("asin", "—"))
col2.metric("Product", selected_row.get("product", "—"))
col3.metric("Division", selected_row.get("division", "—"))
col4.metric("Taxonomy", selected_row.get("taxonomy", "—"))

if "asin_description" in selected_row:
    st.markdown("**Description**")
    st.write(selected_row.get("asin_description", ""))

if "amazon_url" in selected_row and pd.notna(selected_row.get("amazon_url")):
    st.markdown(f"[🔗 View on Amazon]({selected_row['amazon_url']})")

st.divider()

# -------------------------
# Results section (placeholder for now)
# -------------------------
st.subheader("Simulation Results")

else:
    params = SimParams(
        horizon_weeks=horizon_weeks,
        lead_time_weeks=lead_time_weeks,
        review_period_weeks=review_period_weeks,
        service_level=service_level / 100.0,
        safety_factor=safety_factor,
        num_sims=num_sims
    )

    df_asin = filtered_df[filtered_df["asin"] == selected_asin].copy()

    try:
        out = simulate_inventory_po(df_asin, params)
        st.success("Simulation ran successfully ✅")

        r1, r2, r3 = st.columns(3)
        r1.metric("Recommended PO Qty (units)", f"{out['recommended_po_qty']:.0f}")
        r2.metric("Weeks of Cover", f"{out['weeks_of_cover']:.1f}")
        r3.metric("Stockout Risk", f"{out['stockout_risk']*100:.1f}%")

        st.subheader("Inventory trajectory (average across simulations)")
        st.line_chart(out["sim_table"].set_index("week")[["avg_onhand", "forecast_demand"]])

        with st.expander("See simulation table"):
            st.dataframe(out["sim_table"], use_container_width=True)

    except Exception as e:
        st.error(f"Simulation failed: {e}")
