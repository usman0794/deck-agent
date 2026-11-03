"""Core package. Loads .env once, before anything reads environment variables."""
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # optional: real environment variables still work without it
    pass
else:
    # Real environment variables take precedence over values in .env.
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
