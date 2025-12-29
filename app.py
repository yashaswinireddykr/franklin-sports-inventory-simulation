import pandas as pd
import streamlit as st

st.set_page_config(page_title="Franklin Sports Inventory Simulation", layout="wide")

st.title("Franklin Sports — Inventory & PO Simulation (NDA-safe demo)")
st.caption("This app uses masked/synthetic data only. No proprietary Franklin data is included.")

@st.cache_data
def load_data():
    return pd.read_csv("data/masked_merged_sample.csv")

df = load_data()

st.subheader("Dataset preview")
st.write(f"Rows: {df.shape[0]} | Columns: {df.shape[1]}")
st.dataframe(df.head(25), use_container_width=True)

with st.expander("Show column list"):
    st.write(list(df.columns))
