import pandas as pd
from openai import OpenAI
import os


client = OpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
)

def summarize_log(df: pd.DataFrame):
    """
    Summarize test results and integrate LLM for generating a report.
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

def generate_llm_summary(total, passed, failed, error_summary):
    """
    Use OpenAI's GPT to generate a summary and action items based on test results.
    """
    # Validate that the error_summary DataFrame contains the required columns
    required_columns = {"error", "count"}
    if not required_columns.issubset(error_summary.columns):
        return f"Error: The error_summary DataFrame must contain the following columns: {required_columns}"

    # Prepare the prompt
    error_details = "\n".join(
        "- " + error_summary["error"] + ": " + error_summary["count"].astype(str) + " occurrences"
    )
    prompt = f"""
    You are an AI assistant summarizing embedded test results.
    Instructions:
    - Write a concise, technical summary in bullet or paragraph form.
    - Limit the response to **under 500 tokens**.
    - Avoid repeating information. Be focused and efficient.

    Test Summary:
    - Total tests: {total}
    - Passed: {passed}
    - Failed: {failed}
    - Error breakdown:
    {error_details}

    Based on the above data, provide:
    1. A technical summary of test health
    2. Notable failure patterns or trends
    3. Optional action items or next steps
    """

    # Call OpenAI API using the chat/completions endpoint
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
        result = response.choices[0].message.content
        print("Mocked result:", result)
        return result
    except Exception as e:
        return f"Error generating summary: {str(e)}"
