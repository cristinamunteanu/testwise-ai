import pandas as pd
from app.summary import summarize_log

def test_summarize_log():
    # Create a sample DataFrame
    data = {
        "test_case": ["test_1", "test_2", "test_3", "test_4", "test_5"],
        "status": ["PASS", "FAIL", "FAIL", "PASS", "FAIL"],
        "error": ["", "TimeoutError", "ConnectionError", "", "TimeoutError"]
    }
    df = pd.DataFrame(data)

    # Call the summarize_log function
    summary = summarize_log(df)

    # Assertions
    assert summary["total"] == 5, "Total tests should be 5"
    assert summary["passed"] == 2, "Passed tests should be 2"
    assert summary["failed"] == 3, "Failed tests should be 3"

    # Check error summary
    top_errors = summary["top_errors"]
    assert top_errors.shape[0] == 2, "There should be 2 unique errors"
    assert top_errors.loc[top_errors["error"] == "TimeoutError", "count"].iloc[0] == 2, "TimeoutError should appear twice"
    assert top_errors.loc[top_errors["error"] == "ConnectionError", "count"].iloc[0] == 1, "ConnectionError should appear once"