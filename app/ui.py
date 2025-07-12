import streamlit as st
import pandas as pd
import sys
import os
import tempfile

# Set page configuration as the first Streamlit command
st.set_page_config(page_title="Testwise-AI", layout="wide")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.parser import parse_file

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

        if show_only_failed:
            df = df[df["status"] == "FAIL"]

        # Show table
        st.dataframe(df, use_container_width=True)

        # Basic stats
        total = len(df)
        failed = df[df["status"] == "FAIL"].shape[0]
        passed = df[df["status"] == "PASS"].shape[0]

        st.markdown(f"""
        ### 📊 Summary
        - Total Tests: **{total}**
        - ✅ Passed: **{passed}**
        - ❌ Failed: **{failed}**
        """)

        # Chart placeholder (optional)
        st.markdown("### 🔧 Coming next: Error summary, LLM insights, and root cause suggestions")

    except ValueError as e:
        st.error(f"Error while parsing log: {str(e)}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
else:
    st.info("Upload a test log to get started.")
