"""
Custom file tools for Deep Agents framework.

Provides read_file and write_file tools for agent filesystem operations.
"""

import json
from pathlib import Path
from typing import Any, Dict

from langchain_core.tools import tool


@tool
def read_file(file_path: str) -> str:
    """Read the contents of a file.

    Args:
        file_path: Path to the file to read

    Returns:
        File contents as string
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file.

    Args:
        file_path: Path to the file to write
        content: Content to write to the file

    Returns:
        Success message or error
    """
    path = Path(file_path)
    try:
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def read_json(file_path: str) -> Dict[str, Any]:
    """Read and parse a JSON file.

    Args:
        file_path: Path to the JSON file to read

    Returns:
        Parsed JSON data as dict
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"error": f"Error reading JSON: {e}"}


@tool
def write_json(file_path: str, data: Dict[str, Any]) -> str:
    """Write data to a JSON file.

    Args:
        file_path: Path to the JSON file to write
        data: Data to write (must be JSON-serializable)

    Returns:
        Success message or error
    """
    path = Path(file_path)
    try:
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return f"Successfully wrote JSON to {file_path}"
    except Exception as e:
        return f"Error writing JSON: {e}"


__all__ = ["read_file", "write_file", "read_json", "write_json"]
