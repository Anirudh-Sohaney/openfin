"""
data_loader.py
Key objective: Accept all spreadsheet formats and convert them into analyzable pandas DataFrames.

Supported formats: CSV, XLSX, XLS, ODS
"""
import os
import pandas as pd
from typing import Optional, Tuple


def detect_file_format(file_path: str) -> str:
    """Detect the file format from extension."""
    ext = os.path.splitext(file_path)[1].lower()
    format_map = {
        ".csv": "csv",
        ".xlsx": "xlsx",
        ".xls": "xls",
        ".xlsm": "xlsx",
        ".ods": "ods",
        ".tsv": "tsv",
        ".txt": "csv",
    }
    return format_map.get(ext, None)


def load_single_file(file_path: str) -> pd.DataFrame:
    """
    Load a single spreadsheet file into a pandas DataFrame.
    Handles CSV, XLSX, XLS, ODS, and TSV formats.
    """
    fmt = detect_file_format(file_path)
    if fmt is None:
        raise ValueError(f"Unsupported file format: {file_path}")

    if fmt == "csv":
        # Try comma, then tab delimiters
        try:
            df = pd.read_csv(file_path, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding="latin-1")
        # If it looks like TSV (one column with tabs), re-parse
        if df.shape[1] == 1:
            try:
                df = pd.read_csv(file_path, sep="\t", encoding="utf-8")
            except Exception:
                pass
    elif fmt == "tsv":
        df = pd.read_csv(file_path, sep="\t", encoding="utf-8")
    elif fmt == "xlsx":
        df = pd.read_excel(file_path, engine="openpyxl")
    elif fmt == "xls":
        df = pd.read_excel(file_path, engine="xlrd")
    elif fmt == "ods":
        df = pd.read_excel(file_path, engine="odf")
    else:
        raise ValueError(f"Unhandled format: {fmt}")

    return df


def standardize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize the DataFrame:
    - Strip whitespace from column names
    - Convert column names to lowercase with underscores
    - Drop fully empty rows and columns
    - Attempt to convert string columns to numeric where possible
    - Parse date columns
    """
    df = df.copy()

    # Strip whitespace from column names
    df.columns = [str(c).strip() for c in df.columns]

    # Drop completely empty rows and columns
    df = df.dropna(how="all").dropna(axis=1, how="all")

    # Attempt numeric conversion for object/string columns
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]) or str(df[col].dtype) == "str":
            try:
                # Step 1: strip dollar signs and currency symbols (simple string replace)
                cleaned = df[col].str.replace("$", "", regex=False)
                cleaned = cleaned.str.replace("€", "", regex=False)
                cleaned = cleaned.str.replace("£", "", regex=False)
                cleaned = cleaned.str.replace("¥", "", regex=False)
                cleaned = cleaned.str.replace("%", "", regex=False)
                cleaned = cleaned.str.replace("\\", "", regex=False)
                # Step 2: remove comma thousand separators
                cleaned = cleaned.str.replace(",", "", regex=False)
                # Step 3: extract first numeric value from mixed strings like "100 items" -> "100"
                cleaned = cleaned.str.extract(r"(-?\d+\.?\d*)", expand=False)
                cleaned = cleaned.str.strip()

                numeric_series = pd.to_numeric(cleaned, errors="coerce")
                # Only convert if most values become numeric
                if numeric_series.notna().sum() > len(df) * 0.5:
                    df[col] = numeric_series
            except (AttributeError, ValueError):
                pass

    # Attempt date parsing for object/string columns
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]) or str(df[col].dtype) == "str":
            try:
                date_series = pd.to_datetime(df[col], errors="coerce")
                if date_series.notna().sum() > len(df) * 0.5:
                    df[col] = date_series
            except (ValueError, TypeError):
                pass

    return df


def identify_date_column(df: pd.DataFrame) -> Optional[str]:
    """Attempt to identify the primary date column in the DataFrame."""
    # Check datetime columns first
    datetime_cols = df.select_dtypes(include=["datetime64", "datetime64[ns]"]).columns
    if len(datetime_cols) > 0:
        return datetime_cols[0]

    # Check for columns with date-like names
    date_patterns = ["date", "period", "month", "year", "quarter", "time", "day"]
    for col in df.columns:
        col_lower = col.lower().replace(" ", "_")
        if any(p in col_lower for p in date_patterns):
            try:
                date_series = pd.to_datetime(df[col], errors="coerce")
                if date_series.notna().sum() > len(df) * 0.5:
                    return col
            except Exception:
                pass

    return None


def load_and_prepare(file_path: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Main entry point: load a file, standardize it, and identify the date column.

    Returns:
        Tuple of (DataFrame, date_column_name or None)
    """
    df = load_single_file(file_path)
    df = standardize_dataframe(df)
    date_col = identify_date_column(df)
    return df, date_col


def load_all_from_directory(directory: str) -> list:
    """
    Load all spreadsheet files from a directory.
    Returns a list of (file_name, DataFrame, date_column) tuples.
    """
    results = []
    if not os.path.exists(directory):
        return results

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if not os.path.isfile(file_path):
            continue
        fmt = detect_file_format(file_path)
        if fmt is None:
            continue
        try:
            df, date_col = load_and_prepare(file_path)
            results.append((filename, df, date_col))
        except Exception as e:
            print(f"Warning: Could not load {filename}: {e}")
            continue

    return results
