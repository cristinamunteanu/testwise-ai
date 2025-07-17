import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from app.summary import summarize_log, generate_llm_summary

def test_generate_llm_summary_valid_input():
    # Valid input for error_summary
    error_summary = pd.DataFrame({
        "error": ["TimeoutError", "NullReferenceError"],
        "count": [5, 3]
    })
    total = 10
    passed = 7
    failed = 3

    # Mock response for client.chat.completions.create
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Mock summary response"))]

    # Patch the client.chat.completions.create method
    with patch("app.summary.client.chat.completions.create", return_value=mock_response):
        result = generate_llm_summary(total, passed, failed, error_summary)
        assert result == "Mock summary response", f"Expected 'Mock summary response', but got '{result}'"

def test_generate_llm_summary_missing_columns():
    # Missing required columns in error_summary
    error_summary = pd.DataFrame({
        "error_type": ["TimeoutError", "NullReferenceError"],  # Incorrect column name
        "count": [5, 3]
    })
    total = 10
    passed = 7
    failed = 3

    result = generate_llm_summary(total, passed, failed, error_summary)
    
    # Extract the actual missing columns from the error message
    expected_columns = {"error", "count"}
    assert "Error: The error_summary DataFrame must contain the following columns:" in result
    actual_columns = set(result.split(":")[-1].strip(" {}").replace("'", "").split(", "))
    assert actual_columns == expected_columns, f"Expected {expected_columns}, but got {actual_columns}"

def test_generate_llm_summary_api_error():
    # Valid input for error_summary
    error_summary = pd.DataFrame({
        "error": ["TimeoutError", "NullReferenceError"],
        "count": [5, 3]
    })
    total = 10
    passed = 7
    failed = 3

    # Simulate an API error
    def mock_api_error(*args, **kwargs):
        raise Exception("Mock API error")

    # Patch the client.chat.completions.create method
    with patch("app.summary.client.chat.completions.create", side_effect=mock_api_error):
        result = generate_llm_summary(total, passed, failed, error_summary)
        assert result == "Error generating summary: Mock API error"

def test_summarize_log():
    # Test the summarize_log function
    df = pd.DataFrame({
        "test_case": ["test_1", "test_2", "test_3", "test_4", "test_5"],
        "status": ["PASS", "FAIL", "FAIL", "PASS", "FAIL"],
        "module": ["UI", "CORE", "CORE", "UI", "SENSOR"],
        "error": ["", "TimeoutError", "TimeoutError", "", "NullReferenceError"]
    })

    # Mock OpenAI API call
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Mock summary response"))]

    # Patch the OpenAI API call
    with patch("app.summary.client.chat.completions.create", return_value=mock_response):
        summary = summarize_log(df)
        assert summary["total"] == 5
        assert summary["passed"] == 2
        assert summary["failed"] == 3
        assert summary["top_errors"].shape[0] == 2
        assert summary["llm_summary"] == "Mock summary response", f"Expected 'Mock summary response', but got '{summary['llm_summary']}'"