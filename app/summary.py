import pandas as pd

def summarize_log(df: pd.DataFrame):
    total = len(df)
    passed = df[df["status"] == "PASS"].shape[0]
    failed = df[df["status"] == "FAIL"].shape[0]

    error_summary = (
        df[df["status"] == "FAIL"]
        .groupby("error")
        .size()
        .sort_values(ascending=False)
        .reset_index(name="count")
    )

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "top_errors": error_summary
    }
