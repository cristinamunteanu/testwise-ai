import pandas as pd
import re
import os
from typing import Union, IO

def parse_file(file_input: Union[str, IO]) -> pd.DataFrame:
    """
    Parse a test log file (.txt, .log, or .csv) and return a normalized DataFrame.

    Parameters:
        file_input: A file path (str) or file-like object (e.g., from Streamlit uploader)

    Returns:
        pd.DataFrame with columns ["test_case", "status", "error"]
    """
    if isinstance(file_input, str):
        ext = os.path.splitext(file_input)[-1].lower()
    else:
        ext = os.path.splitext(file_input.name)[-1].lower()

    if ext == ".csv":
        return parse_csv(file_input)
    elif ext in [".txt", ".log"]:
        return parse_txt(file_input)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def parse_csv(file_input: Union[str, IO]) -> pd.DataFrame:
    """
    Parse a CSV file containing test results.

    Expected columns (case-insensitive): test_case, status, error
    """
    df = pd.read_csv(file_input)

    # Normalize column names to lowercase
    df.columns = [col.strip().lower() for col in df.columns]
    expected = ["test_case", "status", "error"]

    if not all(col in df.columns for col in expected):
        raise ValueError(f"Missing expected columns in CSV: {expected}")

    return df[expected].copy()


def parse_txt(file_input: Union[str, IO]) -> pd.DataFrame:
    """
    Parse a plain text log file and extract test_case, status, and optional error.

    Expected line format:
        test_case_01: PASS
        test_case_02: FAIL - TimeoutError
    """
    if isinstance(file_input, str):
        # If file_input is a file path, open the file and read lines
        with open(file_input, "r") as f:
            lines = f.readlines()
    else:
        # If file_input is a file-like object, read and decode its content
        lines = file_input.read().decode("utf-8").splitlines()

    results = []
    pattern = re.compile(r"(?P<test_case>\w+): (?P<status>PASS|FAIL)(?: - (?P<error>.+))?")

    for line in lines:
        match = pattern.search(line)
        if match:
            test_case = match.group("test_case")
            status = match.group("status")
            error = match.group("error") or ""
            results.append({
                "test_case": test_case,
                "status": status,
                "error": error.strip()
            })

    return pd.DataFrame(results, columns=["test_case", "status", "error"])
