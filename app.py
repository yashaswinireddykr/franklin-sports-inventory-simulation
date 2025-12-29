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

# Quick KPIs
c1, c2, c3 = st.columns(3)
c1.metric("Rows", f"{df.shape[0]:,}")
c2.metric("Columns", f"{df.shape[1]:,}")
c3.metric("Unique ASINs", f"{df['asin'].nunique():,}" if "asin" in df.columns else "—")

st.divider()

st.subheader("Dataset preview")
st.dataframe(df.head(25), use_container_width=True)

with st.expander("Show column list"):
    st.write(list(df.columns))
