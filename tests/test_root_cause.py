import pandas as pd
from unittest.mock import patch

from app.root_cause import (
    extract_top_errors_with_examples,
    prompt_root_cause_analysis,
    get_root_cause_suggestions,
)

def make_failures_df():
    return pd.DataFrame([
        {"test_case": "tc1", "module": "CORE", "error": "NullPointerException", "status": "FAIL"},
        {"test_case": "tc2", "module": "POWER", "error": "TimeoutError", "status": "FAIL"},
        {"test_case": "tc3", "module": "SENSOR", "error": "TimeoutError", "status": "FAIL"},
        {"test_case": "tc4", "module": "CORE", "error": "NullPointerException", "status": "FAIL"},
        {"test_case": "tc5", "module": "CORE", "error": "NullPointerException", "status": "PASS"},
    ])

def test_extract_top_errors_with_examples():
    df = make_failures_df()
    result = extract_top_errors_with_examples(df, top_n=2)
    assert isinstance(result, dict)
    assert "NullPointerException" in result
    assert "TimeoutError" in result
    assert result["NullPointerException"] == ["tc1", "tc4"]
    assert result["TimeoutError"] == ["tc2", "tc3"]

def test_prompt_root_cause_analysis_format():
    error_examples = {
        "TimeoutError": ["tc2", "tc3"],
        "NullPointerException": ["tc1", "tc4"]
    }
    prompt = prompt_root_cause_analysis(error_examples)
    assert "TimeoutError" in prompt
    assert "NullPointerException" in prompt
    assert "- TimeoutError (e.g. tc2, tc3)" in prompt
    assert "- NullPointerException (e.g. tc1, tc4)" in prompt
    assert "Top Errors:" in prompt

def test_get_root_cause_suggestions_success():
    prompt = "Analyze the following recurring test failures..."
    with patch("app.root_cause.client.chat.completions.create") as mock_create:
        mock_create.return_value.choices = [type("obj", (), {"message": type("obj", (), {"content": "Root cause suggestion"})})()]
        result = get_root_cause_suggestions(prompt)
        assert result == "Root cause suggestion"

def test_get_root_cause_suggestions_error():
    prompt = "Analyze the following recurring test failures..."
    with patch("app.root_cause.client.chat.completions.create", side_effect=Exception("API error")):
        result = get_root_cause_suggestions(prompt)
        assert result.startswith("Error generating root cause suggestions:")

def test_extract_top_errors_with_examples_empty():
    df = pd.DataFrame(columns=["test_case", "module", "error", "status"])
    result = extract_top_errors_with_examples(df)
    assert isinstance(result, dict)
    assert result == {}

def test_prompt_root_cause_analysis_empty():
    prompt = prompt_root_cause_analysis({})
    assert "Top Errors:" in prompt