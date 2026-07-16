import os
from datetime import date

TUNA_PATH = os.path.join(os.path.dirname(__file__), "..", "Tuna.txt")


def append_change(message: str) -> None:
    """Writes one plain-English line to Tuna.txt, like explaining to a 5-year-old."""
    today = date.today().strftime("%B %d, %Y")
    line = f"{today}: {message}\n"
    with open(TUNA_PATH, "a", encoding="utf-8") as f:
        f.write(line)
