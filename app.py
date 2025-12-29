import pandas as pd
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Franklin Sports Inventory Simulation", layout="wide")

st.title("Franklin Sports — Inventory & PO Simulation (NDA-safe demo)")
st.write("✅ App is running and rendering.")

st.subheader("Debug info")
st.write("Current working directory:", Path.cwd())

data_path = Path(__file__).parent / "data" / "masked_merged_sample.csv"
st.write("Looking for file at:", str(data_path))
st.write("File exists:", data_path.exists())

try:
    df = pd.read_csv(data_path)
    st.success(f"Loaded data successfully: {df.shape[0]} rows, {df.shape[1]} columns")
    st.dataframe(df.head(25), use_container_width=True)
    with st.expander("Show column list"):
        st.write(list(df.columns))
except Exception as e:
    st.error("❌ Failed to load the dataset.")
    st.exception(e)
