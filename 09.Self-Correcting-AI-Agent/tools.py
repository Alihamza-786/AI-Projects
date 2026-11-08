"""Tools for the coder agent and the tester agent. All code runs through utils.execute."""

from langchain_core.tools import tool

from utils import (
    CHECK_FILE, SOLUTION_FILE, TEST_FILE,
    execute, pytest_installed, pytest_summary, read_file, write_file,
)


# ---------------- Plain function (not a tool) ----------------

def run_all_tests():
    """Run every test with pytest. Returns (passed, report).
    Used by the run_tests tool AND by our own code to check the tester's claims."""
    if not pytest_installed():
        return False, (
            "SETUP ERROR: pytest is not installed in this Python environment. "
            "Run `pip install pytest`. This is not a bug in solution.py, so the coder cannot fix it."
        )
    if read_file(TEST_FILE) is None:
        return False, "No tests yet. Write them first with write_tests."
    if read_file(SOLUTION_FILE) is None:
        return False, f"{SOLUTION_FILE} does not exist yet, so there is nothing to test."

    # No -x flag: pytest keeps going after a failure, so every failing test is reported at once.
    exit_code, report = execute([
        "-m", "pytest", TEST_FILE, "-q", "--tb=short", "-rfE", "-p", "no:cacheprovider",
    ])
    return exit_code == 0, report


# ---------------- Coder tools ----------------

@tool
def write_code(code: str) -> str:
    """Save the FULL Python code to solution.py (replaces the old file).
    The code must define a function named solve that takes the input as arguments and returns the result."""
    write_file(SOLUTION_FILE, code)
    return f"Saved {SOLUTION_FILE}."


@tool
def read_code() -> str:
    """Read the current solution.py."""
    code = read_file(SOLUTION_FILE)
    return code if code is not None else f"{SOLUTION_FILE} does not exist yet."


@tool
def run_python(snippet: str) -> str:
    """Run a short Python snippet to try the code, for example:
    from solution import solve; print(solve([1, 2, 3]))"""
    write_file(CHECK_FILE, snippet)
    return execute([CHECK_FILE])[1]


# ---------------- Tester tools ----------------

@tool
def write_tests(test_code: str) -> str:
    """Save pytest tests to test_solution.py (replaces the old file).
    Tests must import the function with: from solution import solve"""
    write_file(TEST_FILE, test_code)
    return f"Saved {TEST_FILE}."


@tool
def read_tests() -> str:
    """Read the current test_solution.py."""
    tests = read_file(TEST_FILE)
    return tests if tests is not None else f"{TEST_FILE} does not exist yet."


@tool
def run_tests() -> str:
    """Run ALL tests in test_solution.py with pytest and return the results."""
    return run_all_tests()[1]


coder_tools = [write_code, read_code, run_python]
tester_tools = [write_tests, read_tests, run_tests]
