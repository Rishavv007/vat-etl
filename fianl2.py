import streamlit as st
import pandas as pd
import numpy as np
import re, unicodedata, io, sqlite3
from datetime import datetime

 #currency rates
CURRENCY_RATES = {
    "AED": 1.00,
    "د.إ": 1.00,
    "USD": 3.67,
    "$": 3.67,
    "EUR": 3.98,
    "€": 3.98,
    "GBP": 4.62,
    "£": 4.62,
    "SAR": 0.98,
    "ر.س": 0.98,
    "INR": 0.044,
    "₹": 0.044
}

def detect_and_convert_currency(value):
    """Detect currency symbols or codes and convert to AED."""
    if pd.isna(value):
        return 0.0
    text = str(value).strip()
    detected_currency = "AED"

    # identify currency symbol or code
    for symbol in CURRENCY_RATES.keys():
        if symbol in text:
            detected_currency = symbol
            break

    # remove all non-numeric except ., -, ()
    clean_text = re.sub(r"[^\d\.\-\(\)]", "", text)
    if clean_text.startswith("(") and clean_text.endswith(")"):
        clean_text = "-" + clean_text[1:-1]

    try:
        num = float(clean_text)
    except ValueError:
        num = 0.0

    rate = CURRENCY_RATES.get(detected_currency, 1.0)
    return round(num * rate, 2)

#box mapping
BOX_MAPPING = {
    "Box 1": "Box A",
    "Box 4": "Box B",
    "Box 6": "Box C",
    "Box 10": "Box D"
}

BOX_DESCRIPTIONS = {
    "Box A": "Standard Rated Supplies (5%)",
    "Box B": "Zero Rated Supplies (0%)",
    "Box C": "Recoverable Input VAT",
    "Box D": "Net VAT Payable (BoxA_VAT - BoxC_VAT)"
}

# explicit header mapping
EXACT_HEADER_MAP = {
    "Supply Type": "Supply Type",
    "#": "Invoice Number",
    "Date": "Date",
    "Recoverable": "Recoverable",
    "Customer/supplier Name": "Customer/supplier Name",
    "Net": "Supply/Purchase Value",
    "Tax": "VAT Value",
    "Gross": "Invoice Value",
    "Box": "Box",
}

# helpers
def normalize_header(h):
    if h is None:
        return ""
    s = str(h)
    s = unicodedata.normalize("NFKD", s).replace("\u00A0", " ")
    return s.strip()

def parse_number(v):
    if pd.isna(v):
        return 0.0
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    s = str(v).replace(",", "").replace("$", "").replace(" ", "")
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    s = re.sub(r"[^\d\.\-]", "", s)
    try:
        return float(s)
    except:
        return 0.0

def detect_header_row(df):
    """Find the header row by looking for typical column names."""
    target_keywords = ["supply", "box", "date"]
    for i in range(min(30, len(df))):
        row = df.iloc[i].astype(str).str.lower().tolist()
        match_score = sum(1 for word in target_keywords if any(word in cell for cell in row))
        if match_score >= 2:
            return i
    return 0

# process each sheet
def process_sheet(xls, sheet_name, vat_rate_pct=5.0):
    st.write(f"Reading Sheet: {sheet_name}")

    # read sheet to find header
    df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, dtype=object)
    header_row = detect_header_row(df_raw)
    df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row, dtype=object)

    st.write(f"Detected header row: {header_row + 1}")
    st.write(f"Detected Columns: {list(df.columns)}")

    # normalize headers
    df.columns = [normalize_header(c) for c in df.columns]

    # apply known mappings 
    for col in df.columns:
        if col in EXACT_HEADER_MAP:
            df = df.rename(columns={col: EXACT_HEADER_MAP[col]})

    # ensure all columns exist
    expected_cols = [
        "Supply Type", "Invoice Number", "Date", "Customer/supplier Name",
        "Supply/Purchase Value", "VAT Value", "Invoice Value", "Recoverable", "Box"
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = np.nan

    # clean numeric values + detect currencies
    df["Supply/Purchase Value"] = df["Supply/Purchase Value"].apply(detect_and_convert_currency)
    df["VAT Value"] = df["VAT Value"].apply(detect_and_convert_currency)
    df["Invoice Value"] = df["Invoice Value"].apply(detect_and_convert_currency)

    # convert dates
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Month"] = df["Date"].dt.strftime("%b").fillna(sheet_name)

    # keep original Box letter for reference
    df["BoxLetter"] = df["Box"].astype(str).str.upper().str.replace("BOX", "").str.strip().str[0]

    st.success(f"Processed {len(df)} rows from {sheet_name}")
    st.dataframe(df.head(8))
    return df

# calculate monthly summary
def calculate_summary(df_all):
    results = []
    for m in sorted(df_all["Month"].dropna().unique()):
        sub = df_all[df_all["Month"] == m]

        # compute box-wise totals
        boxA = sub[sub["Box"].astype(str).str.contains("A", case=False, na=False)]
        boxB = sub[sub["Box"].astype(str).str.contains("B", case=False, na=False)]
        boxC = sub[sub["Box"].astype(str).str.contains("C", case=False, na=False)]

        netA, vatA = boxA["Supply/Purchase Value"].sum(), boxA["VAT Value"].sum()
        netB, vatB = boxB["Supply/Purchase Value"].sum(), boxB["VAT Value"].sum()
        netC, vatC = boxC["Supply/Purchase Value"].sum(), boxC["VAT Value"].sum()
        boxD_vat = vatA - vatC

        results.extend([
            {"Month": m, "FTA Box": "Box A", "Description": BOX_DESCRIPTIONS["Box A"], "Net Value": netA, "VAT Value": vatA, "Net VAT Payable": 0},
            {"Month": m, "FTA Box": "Box B", "Description": BOX_DESCRIPTIONS["Box B"], "Net Value": netB, "VAT Value": vatB, "Net VAT Payable": 0},
            {"Month": m, "FTA Box": "Box C", "Description": BOX_DESCRIPTIONS["Box C"], "Net Value": netC, "VAT Value": vatC, "Net VAT Payable": 0},
            {"Month": m, "FTA Box": "Box D", "Description": BOX_DESCRIPTIONS["Box D"], "Net Value": 0, "VAT Value": boxD_vat, "Net VAT Payable": boxD_vat}
        ])

    return pd.DataFrame(results).round(2)

# streamlit app
def main():
    st.set_page_config(page_title="VAT Summary (Box A–D)", layout="wide")
    st.title("VAT Summary — Box A, B, C, D Format (All Values in AED)")

    uploaded = st.file_uploader(" Upload Excel workbook", type=["xlsx"])
    vat_rate = st.sidebar.number_input("📈 VAT Rate (%)", 0.0, 20.0, 5.0, 0.5)

    st.sidebar.subheader("💱 Currency Conversion Rates")
    st.sidebar.json(CURRENCY_RATES)

    if not uploaded:
        st.info("Please upload a workbook with Jan, Feb, etc.")
        return

    xls = pd.ExcelFile(uploaded)
    st.write("Detected Sheets:", xls.sheet_names)

    all_data = []
    for sheet in xls.sheet_names:
        try:
            df = process_sheet(xls, sheet, vat_rate_pct=vat_rate)
            all_data.append(df)
        except Exception as e:
            st.error(f"❌ Error processing {sheet}: {e}")

    if not all_data:
        st.error("No sheets processed.")
        return

    df_all = pd.concat(all_data, ignore_index=True)
    summary = calculate_summary(df_all)

    st.subheader("Monthly VAT Summary (Boxes A–D in AED)")
    st.dataframe(summary)

    # export to Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        summary.to_excel(writer, sheet_name="VAT_Summary", index=False)

    st.download_button(
        label="📥 Download VAT Summary (Excel)",
        data=output.getvalue(),
        file_name=f"vat_summary_AtoD_AED_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # save to SQLite
    try:
        conn = sqlite3.connect("vat_summary.db")
        summary.to_sql("vat_summary", conn, if_exists="replace", index=False)
        conn.close()
    except Exception as e:
        st.warning(f"Could not save to SQLite: {e}")

if __name__ == "__main__":
    main()
