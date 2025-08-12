"""
summary.py

This module provides utilities for summarizing test results from log DataFrames,
including generating technical summaries using a Large Language Model (LLM) such as OpenAI's GPT.

Main features:
- Summarize test results and error patterns from a DataFrame.
- Generate concise, engineering-focused summaries using LLMs.
- Handle large error lists by chunking and combining LLM outputs.
- Optionally disable LLM features via environment variable for test mode.

Functions:
    is_llm_disabled(): Check if LLM features are disabled via environment variable.
    summarize_log(df): Summarize test results and generate an LLM-based summary.
    summarize_chunk(chunk, total, passed, failed, chunk_idx=None, total_chunks=None): Generate an LLM summary for a chunk of errors.
    generate_llm_summary(total, passed, failed, error_summary, chunk_size=50): Generate a technical summary using the LLM, with chunking support.
"""

import pandas as pd
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

def is_llm_disabled():
    """
    Check if LLM (Large Language Model) features are disabled.

    Returns:
        bool: True if the environment variable 'TESTWISE_NO_LLM' is set to "1", otherwise False.
    """
    return os.environ.get("TESTWISE_NO_LLM", "0") == "1"

def summarize_log(df: pd.DataFrame):
    """
    Summarize test results from a DataFrame and generate an LLM-based summary.

    Args:
        df (pd.DataFrame): DataFrame containing test results with at least 'status' and 'error' columns.

    Returns:
        dict: {
            "total": int,         # Total number of tests
            "passed": int,        # Number of passed tests
            "failed": int,        # Number of failed tests
            "top_errors": pd.DataFrame,  # DataFrame of top errors and their counts
            "llm_summary": str    # LLM-generated summary of the results
        }
    """
    # Basic summary statistics
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

    # Generate a summary using LLM
    llm_summary = generate_llm_summary(total, passed, failed, error_summary)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "top_errors": error_summary,
        "llm_summary": llm_summary
    }

def summarize_chunk(chunk, total, passed, failed, chunk_idx=None, total_chunks=None):
    """
    Generate a summary for a chunk of error data using the LLM.

    Args:
        chunk (pd.DataFrame): DataFrame with 'error' and 'count' columns for this chunk.
        total (int): Total number of tests.
        passed (int): Number of passed tests.
        failed (int): Number of failed tests.
        chunk_idx (int, optional): Index of the current chunk (for multi-chunk summaries).
        total_chunks (int, optional): Total number of chunks.

    Returns:
        str: LLM-generated summary for this chunk, or an error message if LLM fails.
    """
    if is_llm_disabled():
        return "[LLM disabled: no summary generated in test mode.]"
    error_details = "\n".join(
        "- " + chunk["error"] + ": " + chunk["count"].astype(str) + " occurrences"
    )
    chunk_info = f" (Chunk {chunk_idx+1}/{total_chunks})" if chunk_idx is not None else ""

    prompt = f"""
    You are a senior QA engineer summarizing automated test results for embedded systems.

    Constraints:
    - Be concise and direct (max 500 tokens)
    - Use engineering tone (clear, factual)
    - Use bullets where helpful
    - Avoid generic language or repetition
    - Highlight what matters most to debugging/fix

    Test Metrics:
    - Total tests: {total}
    - Passed: {passed}
    - Failed: {failed}

    Failure Breakdown:
    {error_details}

    Deliver:
    1. **Test Health Summary** (1–2 sentences)
    2. **Key Failure Patterns** (concise bullet points, sorted by frequency)
    3. **Suggested Actions** (short, high-impact engineering tasks)
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert QA assistant for embedded systems."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def generate_llm_summary(total, passed, failed, error_summary, chunk_size=50):
    """
    Generate a technical summary of test results using the LLM, handling large error lists by chunking.

    Args:
        total (int): Total number of tests.
        passed (int): Number of passed tests.
        failed (int): Number of failed tests.
        error_summary (pd.DataFrame): DataFrame with 'error' and 'count' columns.
        chunk_size (int, optional): Maximum number of errors per chunk for LLM summarization.

    Returns:
        str: LLM-generated summary, or an error message if LLM fails or is disabled.
    """
    if is_llm_disabled():
        return "[LLM disabled: no summary generated in test mode.]"
    required_columns = {"error", "count"}
    if not required_columns.issubset(error_summary.columns):
        return f"Error: The error_summary DataFrame must contain the following columns: {required_columns}"

    n = len(error_summary)
    if n == 0:
        return "No failures to summarize."
    if n <= chunk_size:
        return summarize_chunk(error_summary, total, passed, failed)
    else:
        summaries = []
        total_chunks = (n + chunk_size - 1) // chunk_size
        for i, start in enumerate(range(0, n, chunk_size)):
            chunk = error_summary.iloc[start:start+chunk_size]
            summaries.append(summarize_chunk(chunk, total, passed, failed, i, total_chunks))
        combined_summary = "\n\n".join(summaries)
        if total_chunks > 1:
            final_prompt = (
                "You are an AI assistant. Combine the following chunked summaries into a single, concise technical summary "
                "and action items for the test results. Avoid repetition.\n\n"
                + combined_summary
            )
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an expert QA assistant for embedded systems."},
                        {"role": "user", "content": final_prompt}
                    ],
                    max_tokens=300,
                    temperature=0.3
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"Error generating summary: {str(e)}"
        else:
            return combined_summary


