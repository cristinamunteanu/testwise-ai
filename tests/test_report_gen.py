import os
import tempfile
import pandas as pd

from app.report_gen import (
    generate_markdown_report,
    errors_table_to_list,
    save_report_as_pdf,
)

def make_summary():
    df = pd.DataFrame([
        {"error": "TimeoutError", "count": 3},
        {"error": "NullReferenceException", "count": 2},
    ])
    return {
        "total": 10,
        "passed": 5,
        "failed": 5,
        "top_errors": df,
        "llm_summary": "This is a summary.",
    }

def test_generate_markdown_report_basic():
    summary = make_summary()
    md = generate_markdown_report(summary)
    assert isinstance(md, str)
    assert "# Testwise-AI Report" in md
    assert "TimeoutError" in md
    assert "This is a summary." in md

def test_generate_markdown_report_for_pdf():
    summary = make_summary()
    md = generate_markdown_report(summary, for_pdf=True)
    assert "- **TimeoutError**: 3 failures" in md

def test_generate_markdown_report_with_root_cause():
    summary = make_summary()
    root_cause = "Suspected hardware issue."
    md = generate_markdown_report(summary, root_cause=root_cause)
    assert "Suspected hardware issue." in md

def test_errors_table_to_list():
    df = pd.DataFrame([
        {"error": "TimeoutError", "count": 3},
        {"error": "NullReferenceException", "count": 2},
    ])
    out = errors_table_to_list(df)
    assert "- **TimeoutError**: 3 failures" in out
    assert "- **NullReferenceException**: 2 failures" in out

def test_save_report_as_pdf_creates_pdf():
    summary = make_summary()
    md = generate_markdown_report(summary)
    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = os.getcwd()
        os.chdir(tmpdir)
        pdf_path = save_report_as_pdf(md, filename="testwise_report")
        assert os.path.isfile(pdf_path)
        assert pdf_path.endswith(".pdf")
        os.chdir(cwd)

def test_generate_markdown_report_empty_top_errors():
    summary = make_summary()
    summary["top_errors"] = pd.DataFrame(columns=["error", "count"])
    md = generate_markdown_report(summary)
    assert "Top Failing Errors" in md

def test_generate_markdown_report_missing_llm_summary():
    summary = make_summary()
    summary.pop("llm_summary")
    md = generate_markdown_report(summary)
    assert "## LLM Summary" in md

def test_generate_markdown_report_zero_failed():
    summary = make_summary()
    summary["failed"] = 0
    md = generate_markdown_report(summary)
    assert "Failed: **0**" in md