import pandas as pd
import re
import os
import logging
from typing import Union, IO

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def parse_file(file_input: Union[str, IO]) -> pd.DataFrame:
    """
    Parse a test log file (.txt, .log, or .csv) and return a normalized DataFrame.

    Parameters:
        file_input: A file path (str) or file-like object (e.g., from Streamlit uploader)

    Returns:
        pd.DataFrame with columns ["test_case", "status", "module", "error"]
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
    Parse a plain text or log file and extract test_case, status, module, and optional error.

    Supported formats:
    - Log format:
        [timestamp] ▶ Result: test_case | status | Module: module_name | Error: error_message
    - Text format:
        [timestamp] [RESULT] test_case [module] status - error_message
    - Simple format:
        test_case: status
    """
    if isinstance(file_input, str):
        # If file_input is a file path, open the file and read lines
        logging.debug("Opening file path for reading.")
        with open(file_input, "r") as f:
            lines = f.readlines()
    else:
        # If file_input is a file-like object, read its content once
        logging.debug("Reading file-like object.")
        content = file_input.read()
        if isinstance(content, bytes):
            lines = content.decode("utf-8").splitlines()
        else:
            lines = content.splitlines()

    logging.debug(f"Total lines read: {len(lines)}")

    results = []

    # Regular expressions for different formats
    log_pattern = re.compile(
        r"\[.*?\] ▶ Result: (?P<test_case>\w+) \| (?P<status>PASS|FAIL) \| Module: (?P<module>\w+)(?: \| Error: (?P<error>.+))?"
    )
    txt_pattern = re.compile(
        r"\[RESULT\] (?P<test_case>\w+) \[(?P<module>\w+)\] (?P<status>PASS|FAIL)(?: - (?P<error>.+))?"
    )
    simple_pattern = re.compile(
        r"(?P<test_case>\w+): (?P<status>PASS|FAIL)"
    )

    for line in lines:
        logging.debug(f"Processing line: {line}")
        # Try matching the log format first
        match = log_pattern.search(line)
        if not match:
            # If no match, try the text format
            match = txt_pattern.search(line)
        if not match:
            # If no match, try the simple format
            match = simple_pattern.search(line)

        if match:
            logging.debug(f"Line matched: {line}")
            test_case = match.group("test_case")
            status = match.group("status")
            module = match.group("module") if "module" in match.groupdict() else ""
            error = match.group("error") if "error" in match.groupdict() else None
            results.append({
                "test_case": test_case,
                "status": status,
                "module": module,
                "error": error.strip() if error else ""
            })
        else:
            logging.warning(f"Line did not match any pattern: {line}")

    logging.debug(f"Total valid lines parsed: {len(results)}")
    return pd.DataFrame(results, columns=["test_case", "status", "module", "error"])
