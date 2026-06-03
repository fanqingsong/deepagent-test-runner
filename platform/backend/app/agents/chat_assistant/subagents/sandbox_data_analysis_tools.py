"""
Sandbox Data Analysis Tools — Execute Python code and shell commands in an isolated environment.

These tools are designed to work with LocalShellBackend to provide safe, isolated execution
of arbitrary Python code and shell commands for data analysis tasks.
"""

import json
import logging
import os
import uuid
from typing import Optional

from langchain_core.tools import tool
from deepagents.backends import LocalShellBackend

logger = logging.getLogger(__name__)


def create_sandbox_tools(backend: LocalShellBackend, charts_dir: str):
    """Create sandbox tools that use the provided LocalShellBackend.

    Args:
        backend: LocalShellBackend instance for code execution
        charts_dir: Directory to save generated charts

    Returns:
        List of tool functions for the agent
    """

    @tool
    def execute_python(code: str) -> str:
        """Execute Python code in the sandbox and return the output.

        Args:
            code: Python code to execute. Use print() to return output.

        Examples:
            execute_python("print('Hello World')")
            execute_python("import pandas as pd; df = pd.read_csv('data.csv'); print(df.head())")
        """
        try:
            result = backend.execute(f"python3 -c \"{code}\"")
            return json.dumps({
                "success": True,
                "output": result.stdout,
                "stderr": result.stderr if result.stderr else None,
                "exit_code": result.exit_code,
            }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Python execution error: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    def run_shell_command(command: str) -> str:
        """Execute a shell command in the sandbox.

        Can be used to install packages or run shell utilities.

        Args:
            command: Shell command to execute (e.g., 'pip install seaborn')

        Examples:
            run_shell_command("pip install scipy")
            run_shell_command("ls -la")
        """
        try:
            result = backend.execute(command)
            return json.dumps({
                "success": True,
                "output": result.stdout,
                "stderr": result.stderr if result.stderr else None,
                "exit_code": result.exit_code,
            }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Shell command error: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    def list_files(directory: str = ".") -> str:
        """List files in the sandbox directory.

        Args:
            directory: Directory path to list (default: current directory)

        Returns:
            List of files and directories with metadata
        """
        try:
            result = backend.execute(f"ls -la \"{directory}\"")
            return json.dumps({
                "success": True,
                "directory": directory,
                "files": result.stdout,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    def read_file(filepath: str) -> str:
        """Read a file from the sandbox.

        Args:
            filepath: Path to the file to read

        Returns:
            File contents as text
        """
        try:
            result = backend.execute(f"cat \"{filepath}\"")
            if result.exit_code == 0:
                return json.dumps({
                    "success": True,
                    "filepath": filepath,
                    "content": result.stdout,
                }, ensure_ascii=False)
            return json.dumps({
                "success": False,
                "error": f"Failed to read file: {result.stderr}"
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    def write_file(filepath: str, content: str) -> str:
        """Write content to a file in the sandbox.

        Args:
            filepath: Path to the file to write
            content: Content to write to the file

        Returns:
            Success confirmation
        """
        try:
            # Use echo with heredoc for multi-line content
            escaped_content = content.replace('"', '\\"')
            result = backend.execute(f"echo \"{escaped_content}\" > \"{filepath}\"")
            if result.exit_code == 0:
                return json.dumps({
                    "success": True,
                    "filepath": filepath,
                    "message": f"File written successfully",
                }, ensure_ascii=False)
            return json.dumps({
                "success": False,
                "error": f"Failed to write file: {result.stderr}"
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    def analyze_csv_sandbox(
        csv_filepath: str,
        analysis_type: str = "summary",
    ) -> str:
        """Analyze a CSV file using pandas in the sandbox.

        Args:
            csv_filepath: Path to CSV file in the sandbox
            analysis_type: Type of analysis:
                - "summary": General overview and statistics
                - "correlation": Correlation matrix
                - "distribution": Value distribution
                - "missing": Missing value analysis
        """
        code = f"""
import pandas as pd
import json

df = pd.read_csv("{csv_filepath}")

if "{analysis_type}" == "summary":
    result = {{
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": df.columns.tolist(),
        "dtypes": {{col: str(dt) for col, dt in df.dtypes.items()}},
        "head": df.head().to_dict(orient="records"),
        "describe": df.describe().to_dict()
    }}
    print(json.dumps(result, default=str))

elif "{analysis_type}" == "correlation":
    numeric_df = df.select_dtypes(include=['number'])
    corr = numeric_df.corr()
    result = {{
        "columns": numeric_df.columns.tolist(),
        "correlation_matrix": corr.to_dict()
    }}
    print(json.dumps(result, default=str))

elif "{analysis_type}" == "distribution":
    result = {{}}
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue
        col_info = {{
            "count": len(series),
            "unique": int(series.nunique()),
            "dtype": str(series.dtype)
        }}
        if series.dtype in ['int64', 'float64']:
            col_info["type"] = "numeric"
            col_info["mean"] = float(series.mean())
            col_info["std"] = float(series.std())
        else:
            col_info["type"] = "categorical"
            vc = series.value_counts().head(5)
            col_info["top_values"] = {{str(k): int(v) for k, v in vc.items()}}
        result[col] = col_info
    print(json.dumps(result, default=str))

elif "{analysis_type}" == "missing":
    missing = df.isnull().sum()
    result = {{
        "total_rows": len(df),
        "columns": {{}}
    }}
    for col in df.columns:
        if missing[col] > 0:
            result["columns"][col] = {{
                "missing_count": int(missing[col]),
                "missing_pct": round(float(missing[col] / len(df) * 100), 2)
            }}
    print(json.dumps(result, default=str))
"""
        try:
            result = backend.execute(f'python3 -c "{code}"')
            if result.exit_code == 0:
                return json.dumps({
                    "success": True,
                    "analysis_type": analysis_type,
                    "result": json.loads(result.stdout),
                }, ensure_ascii=False)
            return json.dumps({
                "success": False,
                "error": f"Analysis failed: {result.stderr}"
            }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"CSV analysis error: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    def generate_chart_sandbox(
        csv_filepath: str,
        chart_type: str,
        x_column: str,
        y_column: Optional[str] = None,
        title: str = "Chart",
        output_filename: Optional[str] = None,
    ) -> str:
        """Generate a chart from CSV data using matplotlib in the sandbox.

        Args:
            csv_filepath: Path to CSV file in the sandbox
            chart_type: Type of chart (bar, line, scatter, histogram, pie, box)
            x_column: Column for x-axis
            y_column: Column for y-axis (optional for some chart types)
            title: Chart title
            output_filename: Output filename (optional, auto-generated if not provided)
        """
        if not output_filename:
            output_filename = f"chart_{uuid.uuid4().hex[:12]}.png"

        y_col_param = f'"{y_column}"' if y_column else 'None'

        code = f"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

df = pd.read_csv("{csv_filepath}")
x_col = "{x_column}"
y_col = {y_col_param}

fig, ax = plt.subplots(figsize=(10, 6))

if "{chart_type}" == "bar":
    if y_col:
        df.groupby(x_col)[y_col].sum().plot(kind="bar", ax=ax)
    else:
        df[x_col].value_counts().plot(kind="bar", ax=ax)
    plt.xticks(rotation=45, ha="right")

elif "{chart_type}" == "line":
    if y_col:
        df.plot(x=x_col, y=y_col, kind="line", ax=ax, marker="o")
    else:
        df[x_col].value_counts().plot(kind="line", ax=ax, marker="o")
    plt.xticks(rotation=45, ha="right")

elif "{chart_type}" == "scatter":
    if y_col:
        ax.scatter(df[x_col], df[y_col], alpha=0.7)
    else:
        ax.scatter(df[x_col], df[x_col], alpha=0.7)

elif "{chart_type}" == "histogram":
    col = y_col if y_col else x_col
    ax.hist(df[col].dropna(), bins=30, edgecolor="black", alpha=0.7)

elif "{chart_type}" == "pie":
    df[x_col].value_counts().head(10).plot(kind="pie", ax=ax, autopct="%1.1f%%")
    ax.set_ylabel("")

elif "{chart_type}" == "box":
    import seaborn as sns
    if y_col:
        sns.boxplot(data=df, x=x_col, y=y_col, ax=ax)
    else:
        sns.boxplot(data=df, y=x_col, ax=ax)
    plt.xticks(rotation=45, ha="right")

ax.set_title("{title}", fontsize=14, pad=12)
plt.tight_layout()
plt.savefig("{output_filename}", dpi=150, bbox_inches="tight")
plt.close()

print("SUCCESS:{output_filename}")
"""
        try:
            result = backend.execute(f'python3 -c "{code}"')
            if "SUCCESS:" in result.stdout:
                filename = result.stdout.split("SUCCESS:")[1].strip()
                # Copy file from sandbox to charts directory
                sandbox_path = os.path.join(backend.root_dir, filename)
                target_path = os.path.join(charts_dir, filename)

                # Read from sandbox and write to charts dir
                read_result = backend.execute(f"cat \"{filename}\"")
                if read_result.exit_code == 0:
                    with open(target_path, "wb") as f:
                        # Write binary content
                        f.write(read_result.stdout.encode())

                    chart_url = f"/api/v1/charts/{filename}"
                    return json.dumps({
                        "success": True,
                        "chart_type": chart_type,
                        "chart_url": chart_url,
                        "filename": filename,
                        "message": f"Chart saved. View at: {chart_url}",
                    }, ensure_ascii=False)

            return json.dumps({
                "success": False,
                "error": f"Chart generation failed: {result.stderr}"
            }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Chart generation error: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    def install_package(package_name: str) -> str:
        """Install a Python package in the sandbox.

        Args:
            package_name: Package name to install (e.g., 'scipy', 'plotly')

        Note:
            Only whitelisted packages are allowed for security.
        """
        # Whitelist of allowed packages
        allowed_packages = {
            "scipy", "plotly", "bokeh", "altair", "scikit-learn",
            "statsmodels", "sympy", "networkx", "pillow", "openpyxl"
        }

        if package_name.lower() not in allowed_packages:
            return json.dumps({
                "success": False,
                "error": f"Package '{package_name}' is not in the allowed list. Allowed: {sorted(allowed_packages)}"
            }, ensure_ascii=False)

        try:
            result = backend.execute(f"pip install {package_name}")
            if result.exit_code == 0:
                return json.dumps({
                    "success": True,
                    "package": package_name,
                    "message": f"Package '{package_name}' installed successfully",
                }, ensure_ascii=False)
            return json.dumps({
                "success": False,
                "error": f"Installation failed: {result.stderr}"
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    @tool
    def export_results(results: str, filename: str = "results.json") -> str:
        """Export analysis results to a file.

        Args:
            results: JSON string containing analysis results
            filename: Output filename (default: results.json)
        """
        try:
            # Validate JSON
            json.loads(results)

            escaped = results.replace('"', '\\"')
            result = backend.execute(f'echo "{escaped}" > "{filename}"')

            if result.exit_code == 0:
                return json.dumps({
                    "success": True,
                    "filename": filename,
                    "message": f"Results exported to {filename}",
                }, ensure_ascii=False)
            return json.dumps({
                "success": False,
                "error": f"Export failed: {result.stderr}"
            }, ensure_ascii=False)
        except json.JSONDecodeError:
            return json.dumps({"success": False, "error": "Invalid JSON in results"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    return [
        execute_python,
        run_shell_command,
        list_files,
        read_file,
        write_file,
        analyze_csv_sandbox,
        generate_chart_sandbox,
        install_package,
        export_results,
    ]
