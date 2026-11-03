"""Find the key metric and category in raw data and summarise it."""
import pandas as pd


def analyze(df, metric=None, category=None):
    if df is None or df.empty:
        raise ValueError("The data is empty.")
    df = df.copy()
    num = [c for c in df.columns if pd.to_numeric(df[c], errors="coerce").notna().mean() >= 0.8]
    cats = [c for c in df.columns if c not in num]
    metric = metric if metric in df.columns else (num[0] if num else None)
    # prefer a category that actually groups rows (not a unique id column)
    if category not in df.columns:
        category = next((c for c in cats if df[c].nunique() < len(df)), cats[0] if cats else None)
    if metric:
        df[metric] = pd.to_numeric(df[metric], errors="coerce").fillna(0)
    if category and metric:
        groups = df.groupby(category)[metric].sum()
    elif category:
        groups = df[category].value_counts()
    else:
        groups = pd.Series({"All": float(len(df))})
    groups = groups.sort_values(ascending=False).astype(float)
    total = float(groups.sum())
    return {
        "metric": metric or "Count",
        "category": category or "Group",
        "groups": groups,
        "total": total,
        "top": str(groups.index[0]),
        "low": str(groups.index[-1]),
        "top_share": round(groups.iloc[0] / total * 100) if total else 0,
        "rows": len(df),
    }
