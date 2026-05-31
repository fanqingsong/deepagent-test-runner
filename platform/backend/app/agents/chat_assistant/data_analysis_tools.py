"""
Data Analysis Tools — Analyze data files, generate visualizations, and share results.

Provides tools for the data analysis subagent to perform exploratory data analysis,
compute statistics, and generate charts from CSV/JSON data.
"""

import base64
import io
import json
import logging
import os
import uuid
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

sns.set_style("whitegrid")


def _parse_csv(csv_content: str) -> pd.DataFrame:
    """Parse CSV string into a DataFrame."""
    return pd.read_csv(io.StringIO(csv_content))


def _safe_describe(df: pd.DataFrame) -> dict:
    """Generate a safe statistical summary, converting non-serializable types."""
    desc = df.describe(include="all").to_dict()
    result = {}
    for col, stats in desc.items():
        result[col] = {}
        for stat_name, val in stats.items():
            if pd.isna(val):
                result[col][stat_name] = None
            elif isinstance(val, (np.integer,)):
                result[col][stat_name] = int(val)
            elif isinstance(val, (np.floating, float)):
                result[col][stat_name] = round(float(val), 4)
            else:
                result[col][stat_name] = str(val)
    return result


@tool
def analyze_csv_data(
    csv_content: str,
    analysis_type: str = "summary",
) -> str:
    """Analyze CSV data and return statistical results.

    Args:
        csv_content: CSV data as a string (with headers)
        analysis_type: Type of analysis to perform:
            - "summary": General overview and descriptive statistics (default)
            - "correlation": Correlation matrix between numeric columns
            - "distribution": Value distribution and frequency analysis
            - "missing": Missing value analysis
    """
    try:
        df = _parse_csv(csv_content)
    except Exception as e:
        return json.dumps({"success": False, "error": f"Failed to parse CSV: {e}"}, ensure_ascii=False)

    try:
        if analysis_type == "summary":
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            result = {
                "success": True,
                "analysis_type": "summary",
                "overview": {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": df.columns.tolist(),
                    "dtypes": {col: str(dt) for col, dt in df.dtypes.items()},
                    "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
                },
                "statistics": _safe_describe(df),
                "sample_rows": df.head(5).to_dict(orient="records") if len(df) <= 100 else df.head(3).to_dict(orient="records"),
            }
            if numeric_cols:
                result["numeric_summary"] = {}
                for col in numeric_cols:
                    series = df[col].dropna()
                    result["numeric_summary"][col] = {
                        "mean": round(float(series.mean()), 4) if len(series) else None,
                        "median": round(float(series.median()), 4) if len(series) else None,
                        "std": round(float(series.std()), 4) if len(series) > 1 else None,
                        "min": float(series.min()) if len(series) else None,
                        "max": float(series.max()) if len(series) else None,
                    }

        elif analysis_type == "correlation":
            numeric_df = df.select_dtypes(include=[np.number])
            if numeric_df.empty:
                return json.dumps({"success": False, "error": "No numeric columns found for correlation analysis"}, ensure_ascii=False)
            corr = numeric_df.corr()
            result = {
                "success": True,
                "analysis_type": "correlation",
                "columns": numeric_df.columns.tolist(),
                "correlation_matrix": {},
                "strong_correlations": [],
            }
            for col in corr.columns:
                result["correlation_matrix"][col] = {row: round(float(corr.loc[row, col]), 4) for row in corr.index}
            pairs = []
            cols = corr.columns.tolist()
            for i in range(len(cols)):
                for j in range(i + 1, len(cols)):
                    val = float(corr.iloc[i, j])
                    if abs(val) > 0.5:
                        pairs.append({"col_a": cols[i], "col_b": cols[j], "correlation": round(val, 4)})
            result["strong_correlations"] = sorted(pairs, key=lambda x: abs(x["correlation"]), reverse=True)

        elif analysis_type == "distribution":
            result = {"success": True, "analysis_type": "distribution", "columns": {}}
            for col in df.columns:
                series = df[col].dropna()
                if series.empty:
                    continue
                col_info = {"count": len(series), "unique": int(series.nunique())}
                if series.dtype in [np.number]:
                    col_info["type"] = "numeric"
                    q = series.quantile([0.25, 0.5, 0.75])
                    col_info["quartiles"] = {"q25": round(float(q.iloc[0]), 4), "q50": round(float(q.iloc[1]), 4), "q75": round(float(q.iloc[2]), 4)}
                    col_info["iqr"] = round(float(q.iloc[2] - q.iloc[0]), 4)
                else:
                    col_info["type"] = "categorical"
                    vc = series.value_counts().head(10)
                    col_info["top_values"] = {str(k): int(v) for k, v in vc.items()}
                result["columns"][col] = col_info

        elif analysis_type == "missing":
            total_cells = df.shape[0] * df.shape[1]
            missing = df.isnull().sum()
            result = {
                "success": True,
                "analysis_type": "missing",
                "total_cells": total_cells,
                "total_missing": int(missing.sum()),
                "missing_pct": round(float(missing.sum() / total_cells * 100), 2) if total_cells else 0,
                "columns": {},
            }
            for col in df.columns:
                col_missing = int(missing[col])
                if col_missing > 0:
                    result["columns"][col] = {
                        "missing_count": col_missing,
                        "missing_pct": round(col_missing / len(df) * 100, 2),
                        "dtype": str(df[col].dtype),
                    }

        else:
            return json.dumps({"success": False, "error": f"Unknown analysis_type: {analysis_type}. Use: summary, correlation, distribution, missing"}, ensure_ascii=False)

        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"Data analysis error: {e}")
        return json.dumps({"success": False, "error": str(e)[:500]}, ensure_ascii=False)


@tool
def generate_chart(
    csv_content: str,
    chart_type: str,
    x_column: str,
    y_column: Optional[str] = None,
    title: str = "Chart",
    color_column: Optional[str] = None,
    aggregation: str = "none",
) -> str:
    """Generate a chart from CSV data and return as base64-encoded PNG image.

    Args:
        csv_content: CSV data as a string (with headers)
        chart_type: Type of chart to generate:
            - "bar": Bar chart
            - "line": Line chart
            - "scatter": Scatter plot
            - "histogram": Histogram
            - "pie": Pie chart
            - "box": Box plot
            - "heatmap": Correlation heatmap
            - "pair": Pairwise relationships
        x_column: Column name for x-axis (or category column for pie chart)
        y_column: Column name for y-axis (not needed for histogram, pie uses x for grouping)
        title: Chart title
        color_column: Optional column for color grouping
        aggregation: Aggregation method for bar/line charts:
            - "none": Use raw data (default)
            - "sum": Sum values per x category
            - "mean": Average values per x category
            - "count": Count rows per x category
    """
    try:
        df = _parse_csv(csv_content)
    except Exception as e:
        return json.dumps({"success": False, "error": f"Failed to parse CSV: {e}"}, ensure_ascii=False)

    if x_column not in df.columns:
        return json.dumps({"success": False, "error": f"Column '{x_column}' not found. Available: {df.columns.tolist()}"}, ensure_ascii=False)
    if y_column and y_column not in df.columns:
        return json.dumps({"success": False, "error": f"Column '{y_column}' not found. Available: {df.columns.tolist()}"}, ensure_ascii=False)
    if color_column and color_column not in df.columns:
        return json.dumps({"success": False, "error": f"Column '{color_column}' not found. Available: {df.columns.tolist()}"}, ensure_ascii=False)

    try:
        fig, ax = plt.subplots(figsize=(10, 6))

        if chart_type == "bar":
            plot_df = _aggregate(df, x_column, y_column, aggregation, color_column)
            if color_column and aggregation != "none":
                plot_df.plot(kind="bar", ax=ax, rot=45)
            elif color_column:
                sns.countplot(data=df, x=x_column, hue=color_column, ax=ax)
            else:
                plot_df.plot(kind="bar", ax=ax, rot=45)
            ax.set_xlabel(x_column)
            ax.set_ylabel(y_column or "count")
            plt.xticks(rotation=45, ha="right")

        elif chart_type == "line":
            plot_df = _aggregate(df, x_column, y_column, aggregation, color_column)
            plot_df.plot(kind="line", ax=ax, marker="o")
            ax.set_xlabel(x_column)
            ax.set_ylabel(y_column or "value")
            plt.xticks(rotation=45, ha="right")

        elif chart_type == "scatter":
            if not y_column:
                return json.dumps({"success": False, "error": "scatter chart requires y_column"}, ensure_ascii=False)
            if color_column:
                for cat in df[color_column].unique():
                    mask = df[color_column] == cat
                    ax.scatter(df.loc[mask, x_column], df.loc[mask, y_column], label=cat, alpha=0.7)
                ax.legend()
            else:
                ax.scatter(df[x_column], df[y_column], alpha=0.7)
            ax.set_xlabel(x_column)
            ax.set_ylabel(y_column)

        elif chart_type == "histogram":
            col = x_column if not y_column else y_column
            bins = min(30, max(5, len(df[col].unique())))
            if color_column:
                for cat in df[color_column].unique():
                    mask = df[color_column] == cat
                    ax.hist(df.loc[mask, col], bins=bins, alpha=0.6, label=cat)
                ax.legend()
            else:
                ax.hist(df[col].dropna(), bins=bins, edgecolor="black", alpha=0.7)
            ax.set_xlabel(col)
            ax.set_ylabel("frequency")

        elif chart_type == "pie":
            counts = df[x_column].value_counts()
            counts.head(15).plot(kind="pie", ax=ax, autopct="%1.1f%%", startangle=90)
            ax.set_ylabel("")
            ax.set_aspect("equal")

        elif chart_type == "box":
            if not y_column:
                return json.dumps({"success": False, "error": "box chart requires y_column"}, ensure_ascii=False)
            if color_column:
                sns.boxplot(data=df, x=x_column, y=y_column, hue=color_column, ax=ax)
            else:
                sns.boxplot(data=df, x=x_column, y=y_column, ax=ax)
            plt.xticks(rotation=45, ha="right")

        elif chart_type == "heatmap":
            plt.close(fig)
            numeric_df = df.select_dtypes(include=[np.number])
            if numeric_df.empty:
                return json.dumps({"success": False, "error": "No numeric columns for heatmap"}, ensure_ascii=False)
            fig, ax = plt.subplots(figsize=(max(8, len(numeric_df.columns) * 1.5), max(6, len(numeric_df.columns))))
            corr = numeric_df.corr()
            sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax, square=True)

        elif chart_type == "pair":
            plt.close(fig)
            numeric_df = df.select_dtypes(include=[np.number]).iloc[:, :6]
            if numeric_df.shape[1] < 2:
                return json.dumps({"success": False, "error": "Need at least 2 numeric columns for pair plot"}, ensure_ascii=False)
            pair_grid = sns.pairplot(df[list(numeric_df.columns) + ([color_column] if color_column and color_column in df.columns else [])], hue=color_column if color_column else None)
            fig = pair_grid.fig
            ax = fig.axes[0]
        else:
            plt.close(fig)
            return json.dumps({"success": False, "error": f"Unknown chart_type: {chart_type}"}, ensure_ascii=False)

        ax.set_title(title, fontsize=14, pad=12)
        fig.tight_layout()

        charts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "charts")
        os.makedirs(charts_dir, exist_ok=True)
        filename = f"{uuid.uuid4().hex[:12]}.png"
        filepath = os.path.join(charts_dir, filename)
        fig.savefig(filepath, format="png", dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)

        chart_url = f"/api/v1/charts/{filename}"

        return json.dumps({
            "success": True,
            "chart_type": chart_type,
            "title": title,
            "chart_url": chart_url,
            "message": f"Chart saved. View at: {chart_url}",
        }, ensure_ascii=False)

    except Exception as e:
        plt.close("all")
        logger.error(f"Chart generation error: {e}")
        return json.dumps({"success": False, "error": str(e)[:500]}, ensure_ascii=False)


def _aggregate(df: pd.DataFrame, x_col: str, y_col: Optional[str], agg: str, color_col: Optional[str] = None) -> pd.DataFrame:
    """Aggregate data for bar/line charts."""
    if agg == "none":
        if y_col:
            return df.set_index(x_col)[[y_col]]
        return df[x_col].value_counts().to_frame("count")

    if not y_col and agg != "count":
        return df[x_col].value_counts().to_frame("count")

    group_cols = [x_col] + ([color_col] if color_col else [])
    if agg == "sum":
        return df.groupby(group_cols)[y_col].sum().unstack(fill_value=0) if color_col else df.groupby(x_col)[y_col].sum().to_frame(y_col)
    elif agg == "mean":
        return df.groupby(group_cols)[y_col].mean().unstack(fill_value=0) if color_col else df.groupby(x_col)[y_col].mean().to_frame(y_col)
    elif agg == "count":
        return df.groupby(group_cols).size().unstack(fill_value=0) if color_col else df.groupby(x_col).size().to_frame("count")
    return df.set_index(x_col)[[y_col]] if y_col else df[x_col].value_counts().to_frame("count")


@tool
def run_custom_analysis(
    csv_content: str,
    analysis_code: str,
) -> str:
    """Run a custom Python analysis on CSV data using pandas.

    The CSV data is loaded into a DataFrame variable called 'df'.
    Return the final result as a string (use print() or the last expression).

    Args:
        csv_content: CSV data as a string (with headers)
        analysis_code: Python code to run. The DataFrame 'df' is available.
            Use 'df' for the DataFrame. Print results to return them.
            Available libraries: pandas (as pd), numpy (as np).
    """
    try:
        df = _parse_csv(csv_content)
    except Exception as e:
        return json.dumps({"success": False, "error": f"Failed to parse CSV: {e}"}, ensure_ascii=False)

    try:
        local_vars = {"df": df, "pd": pd, "np": np}
        output_buf = io.StringIO()

        import contextlib
        import builtins
        safe_builtins = {
            k: getattr(builtins, k) for k in [
                "print", "len", "range", "enumerate", "zip", "map", "filter",
                "sorted", "reversed", "sum", "min", "max", "abs", "round",
                "type", "isinstance", "list", "dict", "set", "tuple", "str",
                "int", "float", "bool", "None", "True", "False",
            ] if hasattr(builtins, k)
        }
        with contextlib.redirect_stdout(output_buf):
            exec(analysis_code, {"__builtins__": safe_builtins}, local_vars)

        output = output_buf.getvalue().strip()
        if not output:
            result_var = local_vars.get("_result", "")
            output = str(result_var) if result_var else "(no output)"

        return json.dumps({"success": True, "output": output[:5000]}, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Custom analysis error: {e}")
        return json.dumps({"success": False, "error": str(e)[:500]}, ensure_ascii=False)
