import streamlit as st
import pandas as pd
import numpy as np
import re, unicodedata, io, sqlite3
from datetime import datetime
from collections import Counter  # added for year detection


CURRENCY_RATES = {
    "AED": 1.00, "د.إ": 1.00,
    "USD": 3.67, "$": 3.67,
    "EUR": 3.98, "€": 3.98,
    "GBP": 4.62, "£": 4.62,
    "SAR": 0.98, "ر.س": 0.98,
    "INR": 0.044, "₹": 0.044
}

def detect_and_convert_currency(value):
    """Detects the currency symbol/code and converts numeric part to AED."""
    if pd.isna(value):
        return 0.0
    text = str(value).strip()
    detected_currency = "AED"

    # detect which currency symbol exists
    for symbol in CURRENCY_RATES.keys():
        if symbol in text:
            detected_currency = symbol
            break

    clean_text = re.sub(r"[^\d\.\-\(\)]", "", text)
    if clean_text.startswith("(") and clean_text.endswith(")"):
        clean_text = "-" + clean_text[1:-1]

    try:
        num = float(clean_text)
    except ValueError:
        num = 0.0

    return round(num * CURRENCY_RATES.get(detected_currency, 1.0), 2)

# define vat box 
BOX_DESCRIPTIONS = {
    "Box A": "Standard Rated Supplies (5%)",
    "Box B": "Zero Rated Supplies (0%)",
    "Box C": "Recoverable Input VAT",
    "Box D": "Net VAT Payable (BoxA_VAT - BoxC_VAT)"
}

# header normalization and detection logic
EXACT_HEADER_MAP = {
    "Supply Type": "Supply Type",
    "#": "Invoice Number",
    "Invoice #": "Invoice Number",
    "Invoice No.": "Invoice Number",
    "Date": "Date",
    "Recoverable": "Recoverable",
    "Customer/supplier Name": "Customer/supplier Name",
    "Customer Name": "Customer/supplier Name",
    "Supplier Name": "Customer/supplier Name",
    "Net": "Supply/Purchase Value",
    "Tax": "VAT Value",
    "Gross": "Invoice Value",
    "Box": "Box",
}

def normalize_header(h):
    """Cleans unwanted characters from header names."""
    if h is None:
        return ""
    s = unicodedata.normalize("NFKD", str(h)).replace("\u00A0", " ")
    return s.strip()

def detect_header_row(df):
    """Automatically detect which row in Excel likely contains headers."""
    keywords = ["supply", "box", "date", "tax", "gross", "net"]
    for i in range(min(30, len(df))):
        row = df.iloc[i].astype(str).str.lower().tolist()
        if sum(any(k in c for c in row) for k in keywords) >= 2:
            return i
    return 0

# month + year detection system
MONTHS_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12
}

def extract_month_from_sheet(sheet_name):
    """Detects month from the sheet name (e.g. 'March 2024' → Mar, 3)."""
    s = unicodedata.normalize("NFKD", str(sheet_name))
    s = re.sub(r"[^a-zA-Z0-9]", " ", s).lower()
    for m_name, m_num in MONTHS_MAP.items():
        if m_name in s:
            return m_name.title(), m_num
    match = re.search(r"\b(0?[1-9]|1[0-2])\b", s)
    if match:
        m_num = int(match.group(1))
        return datetime(2000, m_num, 1).strftime("%b"), m_num
    return "Unknown", 0

def parse_date_value(val):
    """Parse multiple Excel or string date formats."""
    if pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return pd.to_datetime(val, errors="coerce")
    if isinstance(val, (int, float)) and 1 < val < 60000:
        return pd.Timestamp("1899-12-30") + pd.to_timedelta(int(val), unit="D")
    try:
        return pd.to_datetime(val, errors="coerce", dayfirst=True)
    except Exception:
        return None

def extract_year_from_date_column(df):
    """Detects most frequent year from Date column."""
    if "Date" not in df.columns:
        return datetime.now().year
    parsed = df["Date"].apply(parse_date_value).dropna()
    if parsed.empty:
        return datetime.now().year
    years = parsed.dt.year.astype(int).tolist()
    counts = Counter(years)
    if len(counts) > 1:
        st.warning(f"Multiple years detected: {dict(counts)} — using most frequent year.")
    return int(max(counts, key=counts.get))

# sheet processor

def process_sheet(xls, sheet_name):
    """Read, clean, normalize one sheet of VAT data."""
    st.write(f"Processing Sheet:...{sheet_name}")
    df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, dtype=object)
    header_row = detect_header_row(df_raw)
    df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row, dtype=object)
    df.columns = [normalize_header(c) for c in df.columns]

    # rename columns as per mapping
    for c in list(df.columns):
        if c in EXACT_HEADER_MAP:
            df.rename(columns={c: EXACT_HEADER_MAP[c]}, inplace=True)

    # ensure all columns exist
    required_cols = [
        "Supply Type", "Invoice Number", "Date", "Customer/supplier Name",
        "Supply/Purchase Value", "VAT Value", "Invoice Value", "Recoverable", "Box"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = np.nan

    # currency conversion
    for c in ["Supply/Purchase Value", "VAT Value", "Invoice Value"]:
        df[c] = df[c].apply(detect_and_convert_currency)

    # month & year detection
    month_abbr, month_num = extract_month_from_sheet(sheet_name)
    year_val = extract_year_from_date_column(df)
    st.write(f"Detected Period...: {month_abbr} {year_val}")

    df["Month"], df["MonthNum"], df["Year"], df["SourceSheet"] = month_abbr, month_num, year_val, sheet_name
    df["Box"] = df["Box"].astype(str).str.upper().str.strip()
    df["BoxLetter"] = df["Box"].str.extract(r"([A-Z])", expand=False)
    return df

# vat summary calculator
def calculate_summary(df_all):
    """Aggregate the VAT box."""
    df_all = df_all.sort_values(by=["Year", "MonthNum"]).reset_index(drop=True)
    results = []

    for (m, y) in df_all[["Month", "Year"]].drop_duplicates().itertuples(index=False, name=None):
        sub = df_all[(df_all["Month"] == m) & (df_all["Year"] == y)]

        def box(letter):
            return sub[sub["Box"].str.contains(letter, na=False)]

        A, B, C = box("A"), box("B"), box("C")
        netA, vatA = A["Supply/Purchase Value"].sum(), A["VAT Value"].sum()
        netB, vatB = B["Supply/Purchase Value"].sum(), B["VAT Value"].sum()
        netC, vatC = C["Supply/Purchase Value"].sum(), C["VAT Value"].sum()
        boxD_vat = vatA - vatC

        period = f"{m} {y}"
        results.extend([
            {"Period": period, "FTA Box": "Box A", "Description": BOX_DESCRIPTIONS["Box A"],
             "Net Value": netA, "VAT Value": vatA, "Net VAT Payable": 0},
            {"Period": period, "FTA Box": "Box B", "Description": BOX_DESCRIPTIONS["Box B"],
             "Net Value": netB, "VAT Value": vatB, "Net VAT Payable": 0},
            {"Period": period, "FTA Box": "Box C", "Description": BOX_DESCRIPTIONS["Box C"],
             "Net Value": netC, "VAT Value": vatC, "Net VAT Payable": 0},
            {"Period": period, "FTA Box": "Box D", "Description": BOX_DESCRIPTIONS["Box D"],
             "Net Value": 0, "VAT Value": boxD_vat, "Net VAT Payable": boxD_vat},
        ])
    return pd.DataFrame(results).round(2)

#streamlit app entry point
def main():
    st.set_page_config(page_title="VAT Summary (Box A–D)", layout="wide")
    st.title("VAT Summary")

    #display currency conversion table
    st.sidebar.header("Currency Conversion Rates (to AED)")
    st.sidebar.caption("All uploaded values automatically converted to AED.")
    st.sidebar.json(CURRENCY_RATES)

    uploaded = st.file_uploader("📤 Upload Excel Workbook", type=["xlsx"])
    if not uploaded:
        st.info("Please upload a workbook with monthly sheets (e.g., Jan, Feb, Mar).")
        return

    xls = pd.ExcelFile(uploaded)
    st.write("Detected Sheets:", xls.sheet_names)

    all_data = []
    for sheet in xls.sheet_names:
        try:
            df = process_sheet(xls, sheet)
            all_data.append(df)
        except Exception as e:
            st.error(f"Error processing {sheet}: {e}")

    if not all_data:
        st.error("No valid sheets processed.")
        return

    df_all = pd.concat(all_data, ignore_index=True)

    # display detected period mapping
    mapping = df_all[["SourceSheet", "Month", "Year"]].drop_duplicates().reset_index(drop=True)
    mapping["Year"] = mapping["Year"].astype(str)
    st.subheader("Detected Periods (Sheet → Month Year)")
    st.dataframe(mapping)

    # generate vat summary
    summary = calculate_summary(df_all)
    st.subheader("VAT Summary (AED)")
    st.dataframe(summary)

    # excel export
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        summary.to_excel(writer, sheet_name="VAT_Summary", index=False)

    st.download_button(
        label=" Download VAT Summary (Excel)",
        data=output.getvalue(),
        file_name=f"vat_summary_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # added sqlite storage for persistence
    try:
        conn = sqlite3.connect("vat_summary.db")
        summary.to_sql("vat_summary", conn, if_exists="replace", index=False)
        conn.close()
        st.success("VAT Summary stored in local SQLite database (vat_summary.db)")
    except Exception as e:
        st.warning(f"Could not save to SQLite: {e}")

# run app
if __name__ == "__main__":
    main()
