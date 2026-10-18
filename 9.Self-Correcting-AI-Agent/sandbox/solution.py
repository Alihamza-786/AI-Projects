def solve(s: str) -> bool:
    # Filter the string to keep only alphanumeric characters and convert to lowercase
    filtered = ''.join(ch.lower() for ch in s if ch.isalnum())
    # Check if the filtered string is a palindrome
    return filtered == filtered[::-1]
