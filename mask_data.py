import os
import re
import hashlib
import numpy as np
import pandas as pd

# ---------------------------
# CONFIG (edit only paths)
# ---------------------------
# Your REAL data (stays private, never pushed)
REAL_INPUT_PATH = "../data_private/inputs/merged_final_verified.xlsx"

# Output MASKED CSV (safe for GitHub)
OUT_DIR = "./data"
OUT_FILE = "masked_merged_sample.csv"   # keep it generic

# How many rows to keep in masked sample (small + safe)
N_SAMPLE_ROWS = 300

# Random seed for reproducibility
SEED = 42
np.random.seed(SEED)

# ---------------------------
# HELPERS
# ---------------------------
def stable_token(value: str, prefix: str, n: int = 6) -> str:
    """Create stable anonymized token like ASIN_ABC123."""
    s = str(value)
    h = hashlib.sha256(s.encode("utf-8")).hexdigest().upper()
    return f"{prefix}_{h[:n]}"

def mask_id_column(series: pd.Series, prefix: str) -> pd.Series:
    return series.astype(str).map(lambda x: stable_token(x, prefix))

def shift_dates(series: pd.Series, shift_days: int = 365) -> pd.Series:
    s = pd.to_datetime(series, errors="coerce")
    return s + pd.to_timedelta(shift_days, unit="D")

def perturb_numeric(series: pd.Series, scale: float = 0.75, noise_pct: float = 0.08) -> pd.Series:
    """
    Multiply by a scale and add mild noise. Keeps shape but hides exact values.
    """
    s = pd.to_numeric(series, errors="coerce")
    noise = np.random.normal(loc=0.0, scale=noise_pct, size=len(s))
    out = s * scale * (1 + noise)
    return out

def clamp_nonnegative(series: pd.Series) -> pd.Series:
    return series.clip(lower=0)

# ---------------------------
# LOAD REAL DATA
# ---------------------------
df = pd.read_excel(REAL_INPUT_PATH)

# ---------------------------
# MASKING RULES (generic + safe)
# ---------------------------

# 1) Mask ID-like columns
# We detect common ID column names; you can add more if needed.
id_like_patterns = [
    r"\basin\b",
    r"\bsku\b",
    r"\bitem\b",
    r"\bproduct\b.*id\b",
    r"\bvendor\b.*id\b",
    r"\bpo\b.*(id|number)\b",
    r"\border\b.*(id|number)\b",
]
for col in df.columns:
    col_l = col.lower()
    if any(re.search(pat, col_l) for pat in id_like_patterns):
        # choose prefix based on column name
        prefix = "ID"
        if "asin" in col_l:
            prefix = "ASIN"
        elif "sku" in col_l:
            prefix = "SKU"
        elif "po" in col_l:
            prefix = "PO"
        elif "order" in col_l:
            prefix = "ORD"
        df[col] = mask_id_column(df[col], prefix)

# 2) Shift date-like columns
date_like_patterns = [r"date", r"week", r"month", r"monday"]
for col in df.columns:
    col_l = col.lower()
    if any(re.search(pat, col_l) for pat in date_like_patterns):
        # only shift if it looks like a date column
        try:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().mean() > 0.6:  # mostly parsable dates
                df[col] = shift_dates(df[col], shift_days=365)
        except Exception:
            pass

# 3) Perturb numeric columns (hides exact Franklin numbers)
num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
for col in num_cols:
    df[col] = perturb_numeric(df[col], scale=0.70, noise_pct=0.10)
    # If it looks like quantity/inventory/demand, ensure nonnegative + round
    col_l = col.lower()
    if any(k in col_l for k in ["qty", "quantity", "units", "inventory", "demand", "forecast", "sales", "order"]):
        df[col] = clamp_nonnegative(df[col]).round(0).astype("Int64")

# 4) Remove super-sensitive columns (optional safety net)
# If you have columns like "brand", "customer_name", "supplier_name", etc., drop them.
drop_patterns = [
    r"customer", r"supplier", r"brand", r"company", r"address", r"email", r"phone", r"name"
]
cols_to_drop = []
for col in df.columns:
    col_l = col.lower()
    if any(re.search(pat, col_l) for pat in drop_patterns):
        cols_to_drop.append(col)
# comment out next line if you prefer to keep these masked instead
df = df.drop(columns=cols_to_drop, errors="ignore")

# 5) Sample a small slice (safer + faster for Streamlit)
if len(df) > N_SAMPLE_ROWS:
    df = df.sample(n=N_SAMPLE_ROWS, random_state=SEED).reset_index(drop=True)

# ---------------------------
# SAVE MASKED DATA
# ---------------------------
os.makedirs(OUT_DIR, exist_ok=True)
out_path = os.path.join(OUT_DIR, OUT_FILE)
df.to_csv(out_path, index=False)

print("✅ Masked sample saved to:", out_path)
print("Rows:", len(df), "| Cols:", len(df.columns))
