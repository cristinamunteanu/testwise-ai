import pandas as pd
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

def is_llm_disabled():
    return os.environ.get("TESTWISE_NO_LLM", "0") == "1"

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

def summarize_chunk(chunk, total, passed, failed, chunk_idx=None, total_chunks=None):
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


