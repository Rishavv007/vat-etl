# VAT Summary Generator

A Python-based pipeline for processing VAT transaction data and generating comprehensive VAT box summaries.

## Overview

This project processes Excel files containing VAT transaction data and automatically calculates VAT box summaries according to standard VAT reporting requirements. The application provides a user-friendly web interface for data upload, processing, and report generation.

## Features

- **Multi-Sheet Excel Processing** - Handles Excel files with multiple sheets (monthly data)
- **Automatic Column Detection** - Intelligently identifies VAT-related columns
- **VAT Box Calculations** - Computes Box A, B, C, and D summaries
- **Database Storage** - Stores processed data in SQLite database
- **Report Generation** - Exports results as Excel files
- **Web Interface** - User-friendly Streamlit-based interface

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Rishavv007/vat-etl.git
cd vat-etl
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
streamlit run fianl2.py
```

2. Open your web browser and navigate to `http://localhost:8501`

3. Upload your Excel file containing VAT transaction data

4. View the processed results and download the VAT summary

## Project Structure

```
vat-etl/
├── fianl2.py           # Main file
├── requirements.txt     # Python dependencies
├── vat_summary.db      # SQLite db
└── README.md          # Project documentation
```

## Technical Stack

- **Python 3.8+** - Core programming language
- **Streamlit** - Web application framework
- **Pandas** - Data manipulation and analysis
- **SQLite** - Lightweight database storage
- **OpenPyXL** - Excel file processing
- **NumPy** - Numerical computations

## Data Processing Workflow

1. **File Upload** - Excel file with VAT transaction data
2. **Column Detection** - Automatic identification of relevant columns
3. **Data Processing** - Calculation of VAT box summaries
4. **Database Storage** - Persistent storage of processed data
5. **Report Generation** - Export of results in Excel format

## Requirements

- Python 3.8 or higher
- Internet connection for initial package installation
- Excel files with VAT transaction data

## Future Enhancements

- Support for additional file formats (CSV, JSON)
- Advanced reporting features
- Multi-user support
