"""
report_gen.py

This module provides utilities for generating test reports in Markdown and PDF formats
from test summary data, including formatting error tables and root cause suggestions.

Main features:
- Generate a Markdown report from a summary dictionary and optional root cause analysis.
- Format error tables as Markdown lists or tables.
- Convert Markdown reports to PDF using pdfkit.

Functions:
    generate_markdown_report(summary, root_cause=None, for_pdf=False): Generate a Markdown report from summary data.
    errors_table_to_list(error_df): Format a DataFrame of errors as a Markdown bullet list.
    save_report_as_pdf(md_content, filename="testwise_report"): Save a Markdown report as PDF.
"""

from datetime import datetime
import markdown2
import pdfkit
import os

def generate_markdown_report(summary: dict, root_cause: str = None, for_pdf=False) -> str:
    """
    Generate a Markdown report from test summary data.

    Args:
        summary (dict): Dictionary containing test summary information. Expected keys:
            - 'total': int, total number of tests
            - 'passed': int, number of passed tests
            - 'failed': int, number of failed tests
            - 'top_errors': pd.DataFrame, DataFrame of top errors and their counts
            - 'llm_summary': str, LLM-generated summary (optional)
        root_cause (str, optional): Root cause analysis or suggestions to include in the report.
        for_pdf (bool, optional): If True, formats error table as a bullet list for PDF output.

    Returns:
        str: The generated Markdown report as a string.
    """
    md = "# Testwise-AI Report\n\n"
    md += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md += "## Summary\n"
    md += f"- Total Tests: **{summary['total']}**\n"
    md += f"- Passed: **{summary['passed']}**\n"
    md += f"- Failed: **{summary['failed']}**\n\n"
    md += "---\n\n"
    md += "## Top Failing Errors\n"
    if for_pdf:
        md += errors_table_to_list(summary['top_errors']) + "\n\n"
    else:
        # Markdown table for web/markdown
        md += summary['top_errors'].to_markdown(index=False) + "\n\n"
    md += "---\n\n"
    md += "## LLM Summary\n"
    md += summary.get("llm_summary", "") + "\n\n"
    md += "---\n\n"
    md += "## Root Cause Suggestions\n"
    if root_cause:
        md += root_cause + "\n"
    return md

def errors_table_to_list(error_df):
    """
    Format a DataFrame of errors as a Markdown bullet list.

    Args:
        error_df (pd.DataFrame): DataFrame with columns 'error' and 'count'.

    Returns:
        str: Markdown-formatted bullet list of errors and their counts.
    """
    lines = []
    for _, row in error_df.iterrows():
        lines.append(f"- **{row['error']}**: {row['count']} failures")
    return "\n".join(lines)

def save_report_as_pdf(md_content: str, filename="testwise_report"):
    """
    Save a Markdown report as a PDF file.

    Args:
        md_content (str): The Markdown content to save and convert.
        filename (str, optional): Base filename for the report (without extension).

    Returns:
        str: Path to the generated PDF file.
    """
    md_path = f"{filename}.md"
    html_path = f"{filename}.html"
    pdf_path = f"{filename}.pdf"

    # Save Markdown
    with open(md_path, "w") as f:
        f.write(md_content)

    # Convert to HTML
    html = markdown2.markdown(md_content)
    with open(html_path, "w") as f:
        f.write(html)

    # Convert to PDF
    pdfkit.from_file(html_path, pdf_path)

    return pdf_path
