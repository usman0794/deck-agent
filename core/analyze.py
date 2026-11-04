"""Find the key metric and category in raw data and summarise it."""
import pandas as pd


def _is_date_column(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        return True
    if s.dtype.kind in "if":
        return False
    sample = s.dropna().astype(str).head(20)
    if sample.empty:
        return False
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        return parsed.notna().mean() >= 0.8
    except Exception:
        return False


def analyze(df, metric=None, category=None):
    """Analyse a dataframe. Degrades gracefully for unfamiliar schemas."""
    if df is None or df.empty:
        raise ValueError("The data is empty.")
    df = df.copy()
    num = [c for c in df.columns
           if pd.api.types.is_numeric_dtype(df[c])
           or pd.to_numeric(df[c], errors="coerce").notna().mean() >= 0.8]
    cats = [c for c in df.columns if c not in num]
    date_cols = [c for c in df.columns if _is_date_column(df[c])]
    date_col = date_cols[0] if date_cols else None

    if metric in df.columns and metric in num:
        metric = metric
    elif num:
        metric = num[0]
    else:
        metric = None

    if category in df.columns:
        category = category
    else:
        category = next((c for c in cats if df[c].nunique() <= max(10, len(df) // 2)), None)

    if metric:
        df[metric] = pd.to_numeric(df[metric], errors="coerce").fillna(0)

    if category and metric:
        groups = df.groupby(category)[metric].sum()
    elif category:
        groups = df[category].value_counts()
    elif metric:
        item_col = next((c for c in cats if df[c].nunique() >= len(df) * 0.8), None)
        groups = df.groupby(item_col)[metric].sum() if item_col is not None else df[metric]
    else:
        groups = pd.Series({"Rows": float(len(df))})

    groups = groups.sort_values(ascending=False).astype(float)
    total = float(groups.sum())

    trend = None
    if date_col and metric:
        try:
            tmp = df[[date_col, metric]].dropna().copy()
            tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
            tmp = tmp.dropna().sort_values(date_col)
            if len(tmp) >= 2:
                head = max(1, len(tmp) // 3)
                first = tmp[metric].iloc[:head].mean()
                last = tmp[metric].iloc[-head:].mean()
                if last > first * 1.05:
                    trend = "up"
                elif last < first * 0.95:
                    trend = "down"
                else:
                    trend = "flat"
        except Exception:
            trend = None

    return {
        "metric": metric or "Count",
        "category": category or "Item",
        "groups": groups,
        "total": total,
        "top": str(groups.index[0]) if len(groups) else "All",
        "low": str(groups.index[-1]) if len(groups) else "All",
        "top_share": round(groups.iloc[0] / total * 100) if total and len(groups) else 0,
        "rows": len(df),
        "date_column": date_col,
        "trend": trend,
    }
