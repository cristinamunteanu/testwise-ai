"""
parser.py

This module provides utilities to parse test log files in CSV, TXT, or LOG formats and normalize them into a pandas DataFrame
with the columns: timestamp, test_case, module, status, error, test_type.

Supported log formats:
- CSV with columns: timestamp, test_case, module, status, error, test_type
- Text/Log with lines like:
    [timestamp] [INFO] Running test: test_case [type=test_type]
    [timestamp] [RESULT] test_case [module] status - error_message

Functions:
    parse_file(file_input): Parse a log file (CSV, TXT, LOG) into a normalized DataFrame.
    parse_txt(file_input): Parse a TXT/LOG file into a normalized DataFrame.
"""

import pandas as pd
import re
import os
import logging
from typing import Union, IO

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

EXPECTED_COLUMNS = ["timestamp", "test_case", "module", "status", "error", "test_type"]

def parse_file(file_input: Union[str, IO]) -> pd.DataFrame:
    """
    Parse a test log file (.csv, .txt, or .log) and return a normalized DataFrame.

    Args:
        file_input (str or IO): Path to the log file or a file-like object.

    Returns:
        pd.DataFrame: DataFrame with columns ['timestamp', 'test_case', 'module', 'status', 'error', 'test_type'].

    Raises:
        ValueError: If required columns are missing in a CSV, or if the file type is unsupported.
    """
    # CSV branch
    if isinstance(file_input, str):
        if file_input.endswith(".csv"):
            df = pd.read_csv(file_input)
            missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
            if missing:
                raise ValueError(f"Missing expected columns: {missing}")
            for col in EXPECTED_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            return df[EXPECTED_COLUMNS]
        elif file_input.endswith(".txt") or file_input.endswith(".log"):
            df = parse_txt(file_input)
        else:
            raise ValueError(f"Unsupported file type: {file_input}")
    else:
        df = parse_txt(file_input)

    # Ensure all expected columns are present
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[EXPECTED_COLUMNS]

def parse_txt(file_input: Union[str, IO]) -> pd.DataFrame:
    """
    Parse a plain text or log file and extract timestamp, test_case, status, module, error, and test_type.

    Supported formats:
    - [timestamp] [INFO] Running test: test_case [type=test_type]
    - [timestamp] [RESULT] test_case [module] status - error_message

    Args:
        file_input (str or IO): Path to the log file or a file-like object.

    Returns:
        pd.DataFrame: DataFrame with columns ['timestamp', 'test_case', 'module', 'status', 'error', 'test_type'].
    """
    if hasattr(file_input, "read"):
        lines = file_input.read().splitlines()
    else:
        with open(file_input, "r") as f:
            lines = f.readlines()

    # Patterns
    info_pattern = re.compile(
        r"\[(?P<timestamp>[\d\-: ]+)\] \[INFO\] Running test: (?P<test_case>\w+) \[type=(?P<test_type>\w+)\]"
    )
    result_pattern = re.compile(
        r"\[(?P<timestamp>[\d\-: ]+)\] \[RESULT\] (?P<test_case>\w+) \[(?P<module>\w+)\] (?P<status>PASS|FAIL)(?: - (?P<error>.+))?"
    )

    # Map test_case to test_type (from INFO lines)
    test_type_map = {}
    results = []

    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        info_match = info_pattern.match(line.strip())
        if info_match:
            d = info_match.groupdict()
            test_type_map[d["test_case"]] = d["test_type"]
            continue

        result_match = result_pattern.match(line.strip())
        if result_match:
            d = result_match.groupdict()
            d["test_type"] = test_type_map.get(d["test_case"], "")
            if "error" not in d or d["error"] is None:
                d["error"] = ""
            results.append(d)

    df = pd.DataFrame(results)
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[EXPECTED_COLUMNS]
