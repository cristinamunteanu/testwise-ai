import pandas as pd
from openai import OpenAI
import os

from app.summary import is_llm_disabled

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
        examples = df[df["error"] == err]["test_case"].head(3).tolist()
        error_examples[err] = examples

    return error_examples

def prompt_root_cause_analysis(error_examples: dict) -> str:
    error_blocks = "\n".join(
        f"- {err} (e.g. {', '.join(examples)})"
        for err, examples in error_examples.items()
    )

    prompt = f"""
You are a senior embedded systems QA engineer. Analyze the following recurring errors and test case examples.

For each error:
- Identify a likely root cause (e.g., uninitialized memory, timing bug, I2C line conflict)
- Suggest a practical fix or test improvement

Top Failures:
{error_blocks}

Format:
- **Error:** ...
  - **Likely Cause:** ...
  - **Suggested Fix:** ...

Instructions:
- Limit your answer to a maximum of 3 concise bullet points per error.
- Keep the total response under 350 words.
- Be specific, technical, and avoid vague advice.
- Do not repeat information.

Respond concisely.
"""
    return prompt

def get_root_cause_suggestions(prompt: str, model="gpt-4"):
    if is_llm_disabled():
        return "[LLM disabled: no root cause suggestions generated in test mode.]"
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an embedded software QA assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating root cause suggestions: {str(e)}"
