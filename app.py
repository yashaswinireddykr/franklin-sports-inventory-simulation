import pandas as pd
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Franklin Sports Inventory Simulation", layout="wide")

st.title("Franklin Sports — Inventory & PO Simulation (NDA-safe demo)")
st.caption("This app uses masked data only. No proprietary Franklin Sports data is included.")

@st.cache_data
def load_data():
    data_path = Path(__file__).parent / "data" / "masked_merged_sample.csv"
    return pd.read_csv(data_path)

df = load_data()

# ---------------------------
# Sidebar: product selection
# ---------------------------
st.sidebar.header("1) Select product")

# Helpful defaults (only use columns if they exist)
asin_col = "asin" if "asin" in df.columns else None
desc_col = "asin_description" if "asin_description" in df.columns else None
division_col = "division" if "division" in df.columns else None
taxonomy_col = "taxonomy" if "taxonomy" in df.columns else None
product_col = "product" if "product" in df.columns else None
url_col = "amazon_url" if "amazon_url" in df.columns else None

if asin_col is None:
    st.error("This dataset does not have an 'asin' column. Please check your masked file.")
    st.stop()

# Optional filters (division/taxonomy)
filtered = df.copy()

if division_col:
    divisions = ["All"] + sorted(filtered[division_col].dropna().unique().tolist())
    sel_div = st.sidebar.selectbox("Division", divisions, index=0)
    if sel_div != "All":
        filtered = filtered[filtered[division_col] == sel_div]

if taxonomy_col:
    taxonomies = ["All"] + sorted(filtered[taxonomy_col].dropna().unique().tolist())
    sel_tax = st.sidebar.selectbox("Taxonomy", taxonomies, index=0)
    if sel_tax != "All":
        filtered = filtered[filtered[taxonomy_col] == sel_tax]

# ASIN dropdown (based on filters)
asins = sorted(filtered[asin_col].dropna().unique().tolist())
selected_asin = st.sidebar.selectbox("ASIN", asins)

# Row for selected ASIN (pick the first match)
row = filtered[filtered[asin_col] == selected_asin].iloc[0]

# ---------------------------
# Main: KPI tiles + summary
# ---------------------------
st.subheader("Selected product summary")

c1, c2, c3, c4 = st.columns(4)

c1.metric("ASIN", selected_asin)
if product_col:
    c2.metric("Product", str(row.get(product_col, "—")))
else:
    c2.metric("Product", "—")

if division_col:
    c3.metric("Division", str(row.get(division_col, "—")))
else:
    c3.metric("Division", "—")

if taxonomy_col:
    c4.metric("Taxonomy", str(row.get(taxonomy_col, "—")))
else:
    c4.metric("Taxonomy", "—")

# Description + link
if desc_col:
    st.write("**Description:**", str(row.get(desc_col, "")))

if url_col and pd.notna(row.get(url_col)):
    st.link_button("Open Amazon link", str(row.get(url_col)))

st.divider()

# ---------------------------
# Data preview (collapsed)
# ---------------------------
with st.expander("Preview masked dataset (optional)"):
    st.write(f"Rows: {df.shape[0]:,} | Columns: {df.shape[1]:,}")
    st.dataframe(df.head(25), use_container_width=True)
