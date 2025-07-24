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

    Returns:
        pd.DataFrame with columns ["test_case", "status", "module", "error", "test_type"]
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

    Expected columns (case-insensitive): test_case, status, module, error, test_type
    """
    df = pd.read_csv(file_input)
    df.columns = [col.strip().lower() for col in df.columns]
    expected = ["test_case", "status", "module", "error", "test_type"]

    # Fill missing columns with empty string
    for col in expected:
        if col not in df.columns:
            df[col] = ""

    return df[expected].copy()

def parse_txt(file_input: Union[str, IO]) -> pd.DataFrame:
    """
    Parse a plain text or log file and extract test_case, status, module, error, and test_type.

    Supported formats:
    - Log format:
        [timestamp] ▶ Result: test_case | status | Module: module_name | Type: test_type | Error: error_message
    - Text format:
        [timestamp] [RESULT] test_case [module] status [type] - error_message
    - Simple format:
        test_case: status [type]
    """
    if isinstance(file_input, str):
        with open(file_input, "r") as f:
            lines = f.readlines()
    else:
        content = file_input.read()
        if isinstance(content, bytes):
            lines = content.decode("utf-8").splitlines()
        else:
            lines = content.splitlines()

    results = []
    test_type_map = {}

    # Patterns
    info_pattern = re.compile(r"\[INFO\] Running test: (?P<test_case>\w+) \[type=(?P<test_type>\w+)\]")
    result_pattern = re.compile(
        r"\[RESULT\] (?P<test_case>\w+) \[(?P<module>\w+)\] (?P<status>PASS|FAIL)(?: - (?P<error>.+))?"
    )

    for line in lines:
        info_match = info_pattern.search(line)
        if info_match:
            test_case = info_match.group("test_case")
            test_type = info_match.group("test_type")
            test_type_map[test_case] = test_type
            continue

        result_match = result_pattern.search(line)
        if result_match:
            test_case = result_match.group("test_case")
            status = result_match.group("status")
            module = result_match.group("module")
            error = result_match.group("error") if "error" in result_match.groupdict() else ""
            test_type = test_type_map.get(test_case, "")
            results.append({
                "test_case": test_case,
                "status": status,
                "module": module,
                "error": error.strip() if error else "",
                "test_type": test_type
            })

    return pd.DataFrame(results, columns=["test_case", "status", "module", "error", "test_type"])
