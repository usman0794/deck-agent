"""Load raw data from CSV, Excel or JSON."""
import io
import pandas as pd


def _read_csv(raw):
    """Parse CSV, sniffing the delimiter and tolerating ragged rows."""
    last = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        attempts = (
            {"sep": None, "engine": "python"},                        # sniff , ; \t |
            {"sep": None, "engine": "python", "on_bad_lines": "skip"},  # skip ragged rows
        )
        for kwargs in attempts:
            try:
                return pd.read_csv(io.StringIO(text), **kwargs)
            except Exception as e:  # ParserError from uneven columns, etc.
                last = e
    raise ValueError(f"Could not parse CSV: {last}")


def load(source, name):
    """source: path or file-like object; name: original file name."""
    name = name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(source)
    if name.endswith(".json"):
        return pd.read_json(source)
    if name.endswith((".csv", ".txt")):
        raw = source.read() if hasattr(source, "read") else open(source, "rb").read()
        return _read_csv(raw if isinstance(raw, bytes) else raw.encode("utf-8"))
    raise ValueError("Unsupported file type. Use CSV, XLSX or JSON.")
