"""
Sandbox Data Analysis Subagent — Analyze data with secure Python code execution.

Uses LocalShellBackend to provide isolated execution environment for arbitrary
Python code and shell commands, following the LangChain deepagents pattern.
"""

import os
from typing import Optional

from deepagents import CompiledSubAgent
from deepagents.backends import LocalShellBackend
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

from app.agents.chat_assistant.subagents.sandbox_data_analysis_tools import create_sandbox_tools
from app.core.agent_config import get_llm


def get_sandbox_backend(user_id: Optional[int] = None) -> LocalShellBackend:
    """Create a LocalShellBackend with isolated workspace.

    Args:
        user_id: Optional user ID for workspace isolation

    Returns:
        Configured LocalShellBackend instance
    """
    # Create user-specific workspace directory
    workspace = f"/tmp/data_analysis_sandbox"
    if user_id:
        workspace = f"{workspace}/user_{user_id}"

    return LocalShellBackend(
        root_dir=workspace,
        virtual_mode=True,  # Enable sandboxing for security
        timeout=120,        # 120 second execution limit
        max_output_bytes=10_000_000,  # 10MB output limit
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": workspace,
            "HOME": workspace,
            "LANG": "en_US.UTF-8",
        },
    )


def create_sandbox_data_analysis_graph(
    llm,
    backend: LocalShellBackend,
    charts_dir: str,
    skills_dir: str,
):
    """Create the compiled graph for the sandbox data analysis subagent.

    Args:
        llm: Language model instance
        backend: LocalShellBackend instance
        charts_dir: Directory to save generated charts
        skills_dir: Directory containing skill files

    Returns:
        Compiled agent graph with middleware stack
    """
    # Import middleware components
    try:
        from deepagents.middleware import FilesystemMiddleware, SkillsMiddleware
        middleware_available = True
    except ImportError:
        # Fallback if deepagents middleware is not available
        middleware_available = False

    # Get sandbox tools
    tools = create_sandbox_tools(backend, charts_dir)

    # Configure middleware stack
    middleware = []
    if middleware_available:
        # FilesystemMiddleware provides file operations (read, write, glob, grep)
        middleware.append(FilesystemMiddleware(backend=backend))

        # SkillsMiddleware loads domain knowledge from skill files
        # Only enable if skills directory exists
        if os.path.exists(skills_dir):
            middleware.append(SkillsMiddleware(backend=backend, sources=[skills_dir]))

        # SummarizationMiddleware compresses context for long sessions
        # Uses the same LLM with backend for context storage
        middleware.append(SummarizationMiddleware(model=llm, backend=backend))

    system_prompt = (
        "You are an advanced data analysis specialist with secure Python code execution capabilities. "
        "You can execute arbitrary Python code, install packages, and perform complex data analysis.\n\n"
        "**Available tools:**\n"
        "1. execute_python(code) — Run Python code and get output\n"
        "2. run_shell_command(command) — Execute shell commands (e.g., pip install)\n"
        "3. list_files(directory) — List files in workspace\n"
        "4. read_file(filepath) — Read file contents\n"
        "5. write_file(filepath, content) — Write content to file\n"
        "6. analyze_csv_sandbox(csv_filepath, analysis_type) — Analyze CSV file\n"
        "7. generate_chart_sandbox(csv_filepath, chart_type, x_column, y_column, title) — Create charts\n"
        "8. install_package(package_name) — Install whitelisted Python packages\n"
        "9. export_results(results, filename) — Export analysis results\n\n"
        "**Workflow:**\n"
        "1. Use list_files to see available files\n"
        "2. Use read_file or analyze_csv_sandbox to examine data\n"
        "3. Use execute_python for custom analysis with pandas/numpy\n"
        "4. Use generate_chart_sandbox to create visualizations\n"
        "5. Use export_results to save findings\n\n"
        "**Best practices:**\n"
        "- Always check df.info() and df.describe() first when analyzing data\n"
        "- Use matplotlib for charts, save with plt.savefig(filename, dpi=150, bbox_inches='tight')\n"
        "- Close plots with plt.close() after saving to free memory\n"
        "- Write analysis reports to report.md for structured output\n"
        "- Use print() to return results from execute_python\n\n"
        "**Chart types:** bar, line, scatter, histogram, pie, box, heatmap\n\n"
        "**Security:**\n"
        "- You can only execute code in your isolated workspace\n"
        "- Package installation is restricted to whitelisted packages\n"
        "- Execution timeout is 120 seconds\n\n"
        "Respond in the same language as the user's message. Explain findings clearly."
    )

    return create_agent(
        model=llm,
        tools=tools,
        middleware=middleware,
        system_prompt=system_prompt,
    )


def get_sandbox_data_analysis_subagent(
    llm,
    user_id: Optional[int] = None,
    charts_dir: Optional[str] = None,
    skills_dir: Optional[str] = None,
) -> CompiledSubAgent:
    """Get the sandbox data analysis subagent.

    Args:
        llm: Language model instance (or will use get_llm() if None)
        user_id: Optional user ID for workspace isolation
        charts_dir: Directory for charts (default: app/agents/charts/)
        skills_dir: Directory containing skills (default: app/agents/chat_assistant/skills/)

    Returns:
        CompiledSubAgent for sandbox data analysis
    """
    # Set default paths
    if charts_dir is None:
        current_dir = os.path.dirname(__file__)
        agents_dir = os.path.dirname(current_dir)
        charts_dir = os.path.join(agents_dir, "charts")

    if skills_dir is None:
        current_dir = os.path.dirname(__file__)
        chat_assistant_dir = os.path.dirname(current_dir)
        skills_dir = os.path.join(chat_assistant_dir, "skills")

    # Ensure directories exist
    os.makedirs(charts_dir, exist_ok=True)

    # Create backend for this user
    backend = get_sandbox_backend(user_id)

    # Create the agent graph
    graph = create_sandbox_data_analysis_graph(
        llm=llm,
        backend=backend,
        charts_dir=charts_dir,
        skills_dir=skills_dir,
    )

    return CompiledSubAgent(
        name="sandbox-data-analysis",
        description=(
            "Advanced data analysis with secure Python code execution. "
            "Can execute arbitrary Python code, install packages, analyze CSV/JSON files, "
            "generate matplotlib/seaborn charts, and perform complex statistical analysis. "
            "Use this for custom data analysis, machine learning preprocessing, "
            "statistical modeling, or when you need to run specific Python code. "
            "All code runs in an isolated sandbox with 120s timeout and resource limits."
        ),
        runnable=graph,
    )
