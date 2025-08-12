import pandas as pd
import os
from unittest.mock import patch, MagicMock
import pytest

from app.summary import summarize_log, summarize_chunk, generate_llm_summary, is_llm_disabled

def make_error_summary(n):
    return pd.DataFrame({
        "error": [f"Error{i}" for i in range(n)],
        "count": [i for i in range(n)]
    })

def test_summarize_chunk_success():
    chunk = pd.DataFrame({"error": ["TimeoutError"], "count": [5]})
    with patch("app.summary.client.chat.completions.create") as mock_create:
        mock_create.return_value.choices = [MagicMock(message=MagicMock(content="Chunk summary"))]
        result = summarize_chunk(chunk, 10, 7, 3)
        assert result == "Chunk summary"

def test_summarize_chunk_api_error():
    chunk = pd.DataFrame({"error": ["TimeoutError"], "count": [5]})
    with patch("app.summary.client.chat.completions.create", side_effect=Exception("API fail")):
        result = summarize_chunk(chunk, 10, 7, 3)
        assert result.startswith("Error generating summary:")

def test_generate_llm_summary_small():
    error_summary = pd.DataFrame({"error": ["TimeoutError"], "count": [5]})
    with patch("app.summary.client.chat.completions.create") as mock_create:
        mock_create.return_value.choices = [MagicMock(message=MagicMock(content="Small summary"))]
        result = generate_llm_summary(10, 7, 3, error_summary, chunk_size=10)
        assert result == "Small summary"

def test_generate_llm_summary_large_chunking():
    error_summary = make_error_summary(120)
    # Patch summarize_chunk to return predictable chunk summaries
    with patch("app.summary.summarize_chunk", side_effect=lambda *a, **kw: f"chunk-{kw.get('chunk_idx', 0)}"):
        # Patch final combine call
        with patch("app.summary.client.chat.completions.create") as mock_create:
            mock_create.return_value.choices = [MagicMock(message=MagicMock(content="Final summary"))]
            result = generate_llm_summary(120, 100, 20, error_summary, chunk_size=50)
            assert result == "Final summary"

def test_generate_llm_summary_no_failures():
    error_summary = pd.DataFrame({"error": [], "count": []})
    result = generate_llm_summary(0, 0, 0, error_summary)
    assert result == "No failures to summarize."

def test_generate_llm_summary_missing_columns():
    error_summary = pd.DataFrame({"err": [1], "count": [1]})
    result = generate_llm_summary(1, 0, 1, error_summary)
    assert "Error: The error_summary DataFrame must contain the following columns:" in result

def test_summarize_log_integration():
    df = pd.DataFrame({
        "test_case": ["t1", "t2", "t3"],
        "status": ["PASS", "FAIL", "FAIL"],
        "module": ["A", "B", "C"],
        "error": ["", "TimeoutError", "NullReferenceError"]
    })
    with patch("app.summary.generate_llm_summary", return_value="LLM summary"):
        result = summarize_log(df)
        assert result["total"] == 3
        assert result["passed"] == 1
        assert result["failed"] == 2
        assert "TimeoutError" in result["top_errors"]["error"].values
        assert result["llm_summary"] == "LLM summary"

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

def test_generate_llm_summary_chunked_but_no_final_combine():
    # This will create just one chunk, so combined_summary is returned directly
    error_summary = pd.DataFrame({
        "error": [f"Error{i}" for i in range(10)],
        "count": [i for i in range(10)]
    })
    # Patch summarize_chunk to return predictable chunk summary
    with patch("app.summary.summarize_chunk", return_value="chunk-0-summary"):
        # Patch client.chat.completions.create to ensure it's NOT called for final combine
        with patch("app.summary.client.chat.completions.create") as mock_create:
            result = generate_llm_summary(10, 5, 5, error_summary, chunk_size=20)
            assert result == "chunk-0-summary"
            # Should only call summarize_chunk, not the final combine
            mock_create.assert_not_called()

def test_is_llm_disabled_env(monkeypatch):
    monkeypatch.setenv("TESTWISE_NO_LLM", "1")
    assert is_llm_disabled() is True
    monkeypatch.setenv("TESTWISE_NO_LLM", "0")
    assert is_llm_disabled() is False

def test_summarize_log_empty_df():
    df = pd.DataFrame(columns=["test_case", "status", "module", "error"])
    with patch("app.summary.generate_llm_summary", return_value="No failures to summarize."):
        summary = summarize_log(df)
        assert summary["total"] == 0
        assert summary["passed"] == 0
        assert summary["failed"] == 0
        assert summary["top_errors"].empty
        assert summary["llm_summary"] == "No failures to summarize."

def test_summarize_chunk_llm_disabled(monkeypatch):
    monkeypatch.setenv("TESTWISE_NO_LLM", "1")
    chunk = pd.DataFrame({"error": ["TimeoutError"], "count": [5]})
    result = summarize_chunk(chunk, 10, 7, 3)
    assert "[LLM disabled" in result

def test_generate_llm_summary_llm_disabled(monkeypatch):
    monkeypatch.setenv("TESTWISE_NO_LLM", "1")
    error_summary = pd.DataFrame({"error": ["TimeoutError"], "count": [5]})
    result = generate_llm_summary(10, 7, 3, error_summary)
    assert "[LLM disabled" in result

def test_generate_llm_summary_missing_columns():
    error_summary = pd.DataFrame({"err": [1], "count": [1]})
    result = generate_llm_summary(1, 0, 1, error_summary)
    assert "Error: The error_summary DataFrame must contain the following columns:" in result

def test_generate_llm_summary_no_failures():
    error_summary = pd.DataFrame({"error": [], "count": []})
    result = generate_llm_summary(0, 0, 0, error_summary)
    assert result == "No failures to summarize."

def test_summarize_chunk_exception():
    chunk = pd.DataFrame({"error": ["TimeoutError"], "count": [5]})
    with patch("app.summary.client.chat.completions.create", side_effect=Exception("API fail")):
        result = summarize_chunk(chunk, 10, 7, 3)
        assert result.startswith("Error generating summary:")

def test_generate_llm_summary_chunk_exception():
    error_summary = pd.DataFrame({"error": [f"Error{i}" for i in range(60)], "count": [i for i in range(60)]})
    # Patch summarize_chunk to raise for the first chunk
    with patch("app.summary.summarize_chunk", side_effect=Exception("Chunk error")):
        with pytest.raises(Exception) as excinfo:
            generate_llm_summary(60, 30, 30, error_summary, chunk_size=50)
        assert "Chunk error" in str(excinfo.value)

def test_generate_llm_summary_final_combine_exception():
    error_summary = pd.DataFrame({"error": [f"Error{i}" for i in range(60)], "count": [i for i in range(60)]})
    # Patch summarize_chunk to return a string, patch client to raise on combine
    with patch("app.summary.summarize_chunk", return_value="chunk-summary"):
        with patch("app.summary.client.chat.completions.create", side_effect=Exception("Combine error")):
            result = generate_llm_summary(60, 30, 30, error_summary, chunk_size=50)
            assert "Error generating summary: Combine error" in result




