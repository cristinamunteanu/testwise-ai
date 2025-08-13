"""
root_cause.py

This module provides utilities for analyzing recurring test failures and generating root cause analysis prompts and suggestions,
optionally using a Large Language Model (LLM) such as OpenAI's GPT.

Main features:
- Extract top failing errors and example test cases from a DataFrame.
- Generate a structured prompt for root cause analysis.
- Obtain root cause suggestions from an LLM based on the generated prompt.

Functions:
    extract_top_errors_with_examples(df, top_n=5): Extract top errors and example test cases from a DataFrame.
    prompt_root_cause_analysis(error_examples): Generate a prompt for root cause analysis from error examples.
    get_root_cause_suggestions(prompt, model="gpt-4"): Get root cause suggestions from an LLM using the prompt.
"""

import pandas as pd
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_top_errors_with_examples(df: pd.DataFrame, top_n=5):
    """
    Extract the top N most frequent errors from failed test cases in the DataFrame,
    along with up to 3 example test cases for each error.

    Args:
        df (pd.DataFrame): DataFrame containing at least 'test_case', 'error', and 'status' columns.
        top_n (int, optional): Number of top errors to extract. Default is 5.

    Returns:
        dict: Mapping of error string to a list of up to 3 example test case names.
    """
    top_errors = (
        df[df["status"] == "FAIL"]
        .groupby("error")
        .size()
        .sort_values(ascending=False)
        .head(top_n)
        .index.tolist()
    )

    error_examples = {}
    for err in top_errors:
        # Only include failed test cases as examples
        examples = df[(df["error"] == err) & (df["status"] == "FAIL")]["test_case"].head(3).tolist()
        error_examples[err] = examples

    return error_examples

def prompt_root_cause_analysis(error_examples: dict) -> str:
    """
    Generate a structured prompt for root cause analysis based on top errors and example test cases.

    Args:
        error_examples (dict): Mapping of error string to a list of example test case names.

    Returns:
        str: A formatted prompt string for LLM-based root cause analysis.
    """
    error_blocks = "\n".join(
        f"- {err} (e.g. {', '.join(examples)})"
        for err, examples in error_examples.items()
    )

    prompt = f"""
Analyze the following recurring test failures and their associated test cases.

For each error:
- Identify the most likely root cause (specific to embedded software)
- Suggest a concrete engineering fix or mitigation

Use this format:
- **Error:** ...
  - **Likely Cause:** ...
  - **Suggested Fix:** ...

Top Errors:
{error_blocks}
"""
    return prompt

def get_root_cause_suggestions(prompt: str, model="gpt-4"):
    """
    Get root cause suggestions from an LLM based on the provided prompt.

    Args:
        prompt (str): The prompt string describing top errors and examples.
        model (str, optional): The LLM model to use (default: "gpt-4").

    Returns:
        str: The LLM-generated root cause suggestions, or an error message if the call fails.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a senior embedded QA engineer who writes structured, technical failure analysis reports."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating root cause suggestions: {str(e)}"