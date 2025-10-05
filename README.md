# VAT Summary Generator

A streamlined VAT processing system for compliance with automatic Excel processing and VAT box calculations.

## Features

- 📊 **Multi-Sheet Excel Support** - Process multiple months in one file
- 💾 **SQLite Database** - Lightweight local data storage
- 📈 **Professional Reports** - Clean VAT summary with monthly breakdowns
- 🔧 **Smart Column Detection** - Automatic mapping of VAT columns
- 📥 **Excel Export** - Download results as Excel files

## Installation

```bash
pip install -r requirements.txt
```

## Usage

**Start the VAT Summary Generator:**
```bash
streamlit run fianl2.py
```

Then open your browser to `http://localhost:8501`

## File Structure

```
vat-etl/
├── fianl2.py           # Main VAT summary generator
├── requirements.txt     # Python dependencies
├── README.md          # This file
└── vat_summary.db     # SQLite database (auto-created)
```

## How It Works

1. **Upload Excel File** - Supports multi-sheet Excel files with VAT data
2. **Smart Column Detection** - Automatic mapping of Supply/Purchase Value, VAT Value, Box columns
3. **Database Storage** - Results saved to SQLite for persistence
4. **Report Generation** - Clean, professional VAT reports with monthly breakdowns


## Technical Stack

- **Python 3.8+** - Core language
- **Streamlit** - Web interface
- **Pandas** - Data processing
- **SQLite** - Database storage
- **OpenPyXL** - Excel file handling
- **NumPy** - Numerical computations
