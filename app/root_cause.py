import pandas as pd
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_top_errors_with_examples(df: pd.DataFrame, top_n=5):
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
