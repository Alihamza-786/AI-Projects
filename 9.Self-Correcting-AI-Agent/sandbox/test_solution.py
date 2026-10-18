import pytest
from solution import solve

@pytest.mark.parametrize("input_str, expected", [
    ("", True),  # empty string considered palindrome
    ("racecar", True),  # simple palindrome
    ("A man, a plan, a canal: Panama", True),  # palindrome ignoring punctuation, spaces, cases
    ("No lemon, no melon", True),  # palindrome ignoring spaces and commas
    ("hello", False),  # not a palindrome
])
def test_is_palindrome(input_str, expected):
    assert solve(input_str) == expected
