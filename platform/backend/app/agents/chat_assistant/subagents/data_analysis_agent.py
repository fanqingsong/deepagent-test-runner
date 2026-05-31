"""
Data Analysis Subagent — Specialized for analyzing data, generating visualizations, and sharing results.

Provides exploratory data analysis, statistical computation, and chart generation.
"""

from deepagents import CompiledSubAgent
from langchain.agents import create_agent

from app.agents.chat_assistant.data_analysis_tools import (
    analyze_csv_data,
    generate_chart,
    run_custom_analysis,
)


def create_data_analysis_graph(llm):
    """Create the compiled graph for the data analysis subagent."""
    return create_agent(
        model=llm,
        tools=[analyze_csv_data, generate_chart, run_custom_analysis],
        system_prompt=(
            "You are a data analysis specialist. You MUST use your tools to analyze data and generate charts. "
            "Do NOT write scripts to files or try to execute shell commands — you can only use the 3 tools provided.\n\n"
            "**Your ONLY tools:**\n"
            "1. analyze_csv_data(csv_content, analysis_type) — pass the raw CSV text as csv_content\n"
            "2. generate_chart(csv_content, chart_type, x_column, y_column, title, ...) — pass the raw CSV text, returns a base64 PNG image\n"
            "3. run_custom_analysis(csv_content, analysis_code) — pass the raw CSV text and short pandas code\n\n"
            "**IMPORTANT rules:**\n"
            "- ALWAYS pass the CSV data as a string directly to the tool's csv_content parameter\n"
            "- NEVER try to save files to disk, write Python scripts, or execute shell commands\n"
            "- NEVER delegate to other agents or subagents\n"
            "- You cannot access the filesystem — all work is done through the 3 tools above\n\n"
            "**Workflow:**\n"
            "1. Call analyze_csv_data(csv_content=..., analysis_type='summary') to get statistics\n"
            "2. Call generate_chart(csv_content=..., chart_type='line', x_column='Date', y_column='Revenue', title='Revenue Trend') to create charts\n"
            "3. Use run_custom_analysis only for calculations the other tools cannot handle\n\n"
            "**Chart type guide:**\n"
            "- Trends over time → chart_type='line', x_column=date column, y_column=value column\n"
            "- Comparisons → chart_type='bar'\n"
            "- Proportions → chart_type='pie'\n"
            "- Relationships → chart_type='scatter'\n"
            "- Distributions → chart_type='histogram'\n"
            "- Correlations → chart_type='heatmap'\n\n"
            "Always explain findings in plain language. Respond in the same language as the user's message.\n"
        ),
    )


def get_data_analysis_subagent(llm):
    """Get the compiled data analysis subagent."""
    return CompiledSubAgent(
        name="data-analysis",
        description=(
            "Analyze data files (CSV), compute statistics, generate charts and visualizations. "
            "Use this when the user wants to explore data, find patterns, compute metrics, "
            "generate plots, or run custom analysis on tabular data."
        ),
        runnable=create_data_analysis_graph(llm),
    )
