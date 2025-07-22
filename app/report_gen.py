from datetime import datetime
import markdown2
import pdfkit
import os

def generate_markdown_report(summary: dict, root_cause: str = None, for_pdf=False) -> str:
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
    # error_df should be a DataFrame with columns 'error' and 'count'
    lines = []
    for _, row in error_df.iterrows():
        lines.append(f"- **{row['error']}**: {row['count']} failures")
    return "\n".join(lines)

def save_report_as_pdf(md_content: str, filename="testwise_report"):
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
