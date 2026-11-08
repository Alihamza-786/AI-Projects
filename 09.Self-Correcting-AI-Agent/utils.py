"""Safe runner: every piece of generated code runs here, inside the sandbox/ folder."""
# pip install pytest
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SANDBOX_DIR = Path(__file__).parent / "sandbox"
SOLUTION_FILE = "solution.py"
TEST_FILE = "test_solution.py"
CHECK_FILE = "_check.py"

TIMEOUT_SECONDS = 10
MAX_OUTPUT_CHARS = 3000

# Minimal environment: generated code cannot read OPENAI_API_KEY, DATABASE_URL, etc.
SAFE_ENV = {
    "PATH": os.environ.get("PATH", ""),
    "PYTHONIOENCODING": "utf-8",
    "PYTHONDONTWRITEBYTECODE": "1",
    "COLUMNS": "200",  # wider output so pytest does not cut error messages short
}


def reset_sandbox():
    """Start a new task with an empty sandbox folder."""
    shutil.rmtree(SANDBOX_DIR, ignore_errors=True)
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)


def strip_code_fences(code):
    """LLMs often wrap code in ```python ... ```. Remove that so the file is valid Python."""
    code = code.strip()
    match = re.match(r"^```[a-zA-Z]*\n(.*?)\n?```$", code, re.DOTALL)
    return match.group(1) if match else code


def write_file(name, content):
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    (SANDBOX_DIR / name).write_text(strip_code_fences(content) + "\n", encoding="utf-8")


def read_file(name):
    """Return the file's text, or None if it does not exist."""
    path = SANDBOX_DIR / name
    return path.read_text(encoding="utf-8") if path.exists() else None


def pytest_installed():
    """Generated code runs with this same Python, so check pytest here."""
    return importlib.util.find_spec("pytest") is not None


def _shorten(text):
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + "\n...(output truncated)"
    return text


def execute(args):
    """Run `python <args>` inside sandbox/.
    Returns (exit_code, report_text). exit_code is None if it timed out.

    Limits: own folder, timeout, no secrets in the environment, no shell.
    This is NOT a real security sandbox (the code can still open absolute paths).
    For real isolation, run this inside a Docker container instead.
    """
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [sys.executable, *args],   # a list of args, no shell=True, so no shell tricks
            cwd=SANDBOX_DIR,           # files are created inside sandbox/
            env=SAFE_ENV,              # no API keys
            stdin=subprocess.DEVNULL,  # input() fails fast instead of hanging
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,   # stop infinite loops
        )
    except subprocess.TimeoutExpired:
        return None, f"Error: stopped after {TIMEOUT_SECONDS} seconds (infinite loop or waiting for input?)."

    report = (
        f"EXIT CODE: {result.returncode}\n"
        f"STDOUT:\n{_shorten(result.stdout)}\n"
        f"STDERR:\n{_shorten(result.stderr)}"
    )
    return result.returncode, report


def pytest_summary(report):
    """Pull the real numbers out of pytest output: the count line and the FAILED lines."""
    lines = report.splitlines()
    counts = next(
        (line.strip(" =") for line in reversed(lines) if re.search(r"\d+ (passed|failed|error)", line)),
        "no test results found",
    )
    failed = [line for line in lines if line.startswith(("FAILED ", "ERROR "))]
    return counts, failed
