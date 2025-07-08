import re

def context_windows(text: str, word: str, n: int = 5):
    """
    Finds all occurrences of `word` and returns up to `n` words before and after each,
    including punctuation.
    """
    # \w+[^\s\w]* allows punctuation like "banana," or "banana."
    # \s+ matches spaces/newlines etc.
    pattern = (
        rf'(?:\b\w+[^\s\w]*\s+){{0,{n}}}'         # up to n words before
        rf'\b{re.escape(word)}[^\s\w]*'            # the word itself with optional punctuation
        rf'(?:\s+\w+[^\s\w]*){{0,{n}}}'            # up to n words after
    )

    return re.findall(pattern, text, flags=re.IGNORECASE)

string = "I love to eat a fresh banana in the morning, and banana, smoothies at night!"
match = "banana"

matches = context_windows(string, match, 5)
for i, m in enumerate(matches, 1):
    print(f"Match {i}: → \"{m}\"")