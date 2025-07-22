import streamlit as st
import pandas as pd
import sys
import os
import tempfile
import re

def strip_emojis(text):
    import re
    # Remove most emojis and symbols
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002700-\U000027BF"  # dingbats
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    # Remove surrogate pairs and non-ASCII (covers broken emoji encodings)
    non_ascii_pattern = re.compile(r'[^\x00-\x7F]+')
    text = emoji_pattern.sub(r'', text)
    text = non_ascii_pattern.sub(r'', text)
    return text

# Set page configuration as the first Streamlit command
st.set_page_config(page_title="Testwise-AI", layout="wide")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.parser import parse_file
from app.summary import summarize_log
from app.root_cause import (
    extract_top_errors_with_examples,
    prompt_root_cause_analysis,
    get_root_cause_suggestions,
)
from app.report_gen import generate_markdown_report, save_report_as_pdf


st.title("🧪 Testwise-AI — Log Analyzer")

st.markdown("""
Upload a `.txt`, `.log`, or `.csv` test log to extract test results, view failures, and start summarizing insights.
""")

# File upload
uploaded_file = st.file_uploader("Upload a test log", type=["txt", "csv", "log"])

if uploaded_file:
    try:
        # Save the uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as temp_file:
            temp_file.write(uploaded_file.read())
            temp_path = temp_file.name

        # Parse the file using its temporary path
        df = parse_file(temp_path)

        # Clean up the temporary file
        os.unlink(temp_path)

        st.success(f"Parsed {len(df)} test cases.")
        
        # Filter options
        st.sidebar.header("🔍 Filter")
        show_only_failed = st.sidebar.checkbox("Show only FAILED tests", value=False)

        # Use summarize_log helper function on the original DataFrame
        summary = summarize_log(df)

        # Display summary
        st.markdown("### 📈 Test Summary")
        st.markdown(f"- **Total tests:** {summary['total']}")
        st.markdown(f"- ✅ Passed: {summary['passed']}")
        st.markdown(f"- ❌ Failed: {summary['failed']}")

        # Apply filter for display purposes
        if show_only_failed:
            df = df[df["status"] == "FAIL"]

        # Show filtered or unfiltered DataFrame
        st.dataframe(df, use_container_width=True)

        # Error breakdown
        if summary["failed"] > 0:
            st.markdown("### 🔍 Top Failing Error Types")
            st.dataframe(summary["top_errors"])
            st.bar_chart(summary["top_errors"].set_index("error"))

        # Display LLM-generated summary
        st.markdown("### 🤖 LLM-Generated Summary")
        st.markdown(summary["llm_summary"])

        # Download button for LLM-generated summary as Markdown
        st.download_button(
            label="Download Summary as Markdown",
            data=f"# LLM-Generated Summary\n\n{summary['llm_summary']}",
            file_name="summary_output.md",
            mime="text/markdown"
        )

    except ValueError as e:
        st.error(f"Error while parsing log: {str(e)}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
else:
    st.info("Upload a test log to get started.")

st.markdown("## 🔍 Root Cause Suggestions")

if "root_summary" not in st.session_state:
    st.session_state.root_summary = None

if st.button("🧠 Analyze Top Failures"):
    with st.spinner("Running GPT analysis..."):
        top_errors = extract_top_errors_with_examples(df)
        root_prompt = prompt_root_cause_analysis(top_errors)
        root_summary = get_root_cause_suggestions(root_prompt)
        st.session_state.root_summary = root_summary  # <-- Store in session_state

    st.markdown("### 📄 Root Cause Report")
    st.markdown(st.session_state.root_summary)

    if st.download_button("💾 Download Root Cause Report", st.session_state.root_summary, file_name="root_cause.md"):
        st.success("Report downloaded.")

st.markdown("## 📥 Downloadable Report")

if st.button("📄 Generate Markdown + PDF Report"):
    with st.spinner("Generating report..."):
        markdown = generate_markdown_report(summary, root_cause=st.session_state.get("root_summary", None))
        markdown_no_emoji = strip_emojis(generate_markdown_report(summary, root_cause=st.session_state.get("root_summary", None), for_pdf=True))
        pdf_path = save_report_as_pdf(markdown_no_emoji)
        st.session_state.generated_pdf = pdf_path
        st.session_state.generated_md = markdown

    st.success("✅ Report generated!")
    st.download_button(
        label="⬇️ Download PDF",
        data=open(st.session_state.generated_pdf, "rb").read(),
        file_name="testwise_report.pdf",
        mime="application/pdf"
    )

    st.download_button(
        label="⬇️ Download Markdown",
        data=st.session_state.generated_md,
        file_name="testwise_report.md",
        mime="text/markdown"
    )


