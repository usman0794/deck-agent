"""Understand the data (stage 1) and the user's situation (stage 2)."""
import difflib
import json
import re
import warnings

import pandas as pd
from core import research

INCREASE_WORDS = ("increase", "raise", "grow", "improve", "higher", "more", "boost", "lift")
REDUCE_WORDS = ("reduce", "cut", "lower", "decrease", "save", "less", "drop", "shrink")


def profile_data(df):
    """Profile a dataframe: rows, columns, types, missing %, duplicates, numeric ranges, outliers, groups."""
    profile = {
        "rows": int(len(df)),
        "columns": {},
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric": {},
        "categories": {},
        "date_columns": [],
        "trend": None,
    }
    for col in df.columns:
        s = df[col]
        profile["columns"][col] = {
            "type": str(s.dtype),
            "missing_pct": round(float(s.isna().mean() * 100), 1),
            "unique": int(s.nunique()),
        }
        if s.dtype.kind in "if":
            vals = s.dropna()
            if len(vals):
                q1, q3 = vals.quantile([0.25, 0.75])
                iqr = q3 - q1
                low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                profile["numeric"][col] = {
                    "min": float(vals.min()),
                    "max": float(vals.max()),
                    "mean": round(float(vals.mean()), 2),
                    "outliers": int(((vals < low) | (vals > high)).sum()),
                }
        elif s.nunique() <= max(10, len(df) // 2):
            profile["categories"][col] = {"groups": int(s.nunique())}
    # date columns and trend
    for col in df.columns:
        s = df[col]
        if s.dtype.kind in "if":
            continue
        sample = s.dropna().astype(str).head(20)
        if sample.empty:
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
            if parsed.notna().mean() >= 0.8:
                profile["date_columns"].append(col)
        except Exception:
            pass
    if profile["date_columns"]:
        date_col = profile["date_columns"][0]
        numeric_cols = list(profile["numeric"].keys())
        if numeric_cols:
            metric_col = numeric_cols[0]
            try:
                tmp = df[[date_col, metric_col]].dropna().copy()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce", format="mixed")
                tmp = tmp.dropna().sort_values(date_col)
                if len(tmp) >= 2:
                    head = max(1, len(tmp) // 3)
                    first = tmp[metric_col].iloc[:head].mean()
                    last = tmp[metric_col].iloc[-head:].mean()
                    if last > first * 1.05:
                        profile["trend"] = "up"
                    elif last < first * 0.95:
                        profile["trend"] = "down"
                    else:
                        profile["trend"] = "flat"
            except Exception:
                pass
    return profile


def guess_columns(df, profile):
    """Rule-based guess of the metric and group columns."""
    numeric = list(profile["numeric"].keys())
    categories = list(profile["categories"].keys())
    return {"metric": numeric[0] if numeric else None,
            "group": categories[0] if categories else None}


def _fuzzy_find(text, candidates, threshold=0.6):
    """Return (best_candidate, score) using substring and difflib word matching."""
    lower = text.lower()
    words = [w for w in re.split(r"[^a-z0-9]+", lower) if len(w) >= 3]
    best, best_score = None, 0.0
    for cand in candidates:
        cand_lower = str(cand).lower()
        if cand_lower in lower:
            return cand, 1.0
        for w in words:
            for cw in re.split(r"[_\s]+", cand_lower):
                score = difflib.SequenceMatcher(None, w, cw).ratio()
                if score > best_score:
                    best, best_score = cand, score
    return (best, best_score) if best_score >= threshold else (None, best_score)


def interpret_data(df, profile, cfg, use_ai):
    """Return a plain-language summary of the dataset (AI or rule-based)."""
    columns = list(df.columns)
    sample = df.head(10).to_dict(orient="records")
    if use_ai and research.available(cfg):
        try:
            prompt = (
                "You are a data analyst. Profile the dataset and return JSON with keys: "
                "{\"about\": one sentence on what this dataset is, "
                "\"columns\": {column name: likely meaning}, "
                "\"quality_notes\": [up to 3 short data-quality notes], "
                "\"suggested_metric\": a numeric column name, "
                "\"suggested_group\": a categorical column name}.\n\n"
                f"Columns: {columns}\nProfile: {json.dumps(profile)[:2000]}\n"
                f"Sample rows: {json.dumps(sample)[:2000]}"
            )
            data = research.complete_json(prompt, cfg)
            return {
                "about": str(data.get("about", "")).strip(),
                "columns": {str(k): str(v) for k, v in data.get("columns", {}).items()},
                "quality_notes": [str(x).strip() for x in data.get("quality_notes", []) if str(x).strip()][:3],
                "suggested_metric": data.get("suggested_metric") if data.get("suggested_metric") in columns else None,
                "suggested_group": data.get("suggested_group") if data.get("suggested_group") in columns else None,
                "profile": profile,
                "trend": profile.get("trend"),
                "mode": "ai",
            }
        except Exception:
            pass
    guess = guess_columns(df, profile)
    notes = []
    if profile["duplicate_rows"]:
        notes.append(f"{profile['duplicate_rows']} duplicate rows")
    for col, info in profile["columns"].items():
        if info["missing_pct"] > 0:
            notes.append(f"{col} is {info['missing_pct']}% missing")
    about = f"Dataset with {profile['rows']} rows and {len(columns)} columns."
    if profile.get("trend"):
        about += f" Trend over time: {profile['trend']}."
    return {
        "about": about,
        "columns": {c: profile["columns"][c]["type"] for c in columns},
        "quality_notes": notes[:3],
        "suggested_metric": guess["metric"],
        "suggested_group": guess["group"],
        "profile": profile,
        "trend": profile.get("trend"),
        "mode": "rules",
    }


def understand_user(text, columns, cfg, use_ai, df=None, numeric_columns=None, categorical_columns=None):
    """Extract problem, goal, metric, group, constraints and audience from plain words."""
    text = (text or "").strip()
    group_values = {}
    if df is not None:
        for col in columns:
            try:
                group_values[col] = [str(v) for v in df[col].dropna().unique().tolist()[:50]]
            except Exception:
                group_values[col] = []
    if use_ai and research.available(cfg):
        try:
            prompt = (
                "Extract the user's intent from the text. Return JSON with keys: "
                "{\"problem\": short problem statement, \"goal\": \"increase\" or \"reduce\", "
                "\"metric\": one of the column names or null, \"group\": one of the column names or null, "
                "\"constraints\": {\"budget\": string or null, \"time\": string or null}, "
                "\"audience\": string}.\n\n"
                f"Columns: {columns}\nGroup values: {json.dumps(group_values)[:1500]}\nText: {text}"
            )
            data = research.complete_json(prompt, cfg)
            return {
                "problem": str(data.get("problem", text)).strip(),
                "goal": data.get("goal") if data.get("goal") in ("increase", "reduce") else None,
                "metric": data.get("metric") if data.get("metric") in columns else None,
                "group": data.get("group") if data.get("group") in columns else None,
                "constraints": data.get("constraints") or {},
                "audience": str(data.get("audience", "leadership")).strip(),
                "mode": "ai",
                "confidence": 0.8,
                "unresolved": [],
            }
        except Exception:
            pass
    lower = text.lower()
    # direction
    goal = None
    if any(w in lower for w in INCREASE_WORDS):
        goal = "increase"
    elif any(w in lower for w in REDUCE_WORDS):
        goal = "reduce"
    # fuzzy match columns and group values
    metric_cols = numeric_columns if numeric_columns is not None else columns
    group_cols = categorical_columns if categorical_columns is not None else columns
    metric, metric_score = _fuzzy_find(text, metric_cols)
    group, group_score = _fuzzy_find(text, [c for c in group_cols if c != metric])
    matched_groups = []
    for col in group_cols:
        for v in group_values.get(col, []):
            m, s = _fuzzy_find(text, [v])
            if m and s >= 0.8:
                matched_groups.append({"column": col, "value": v, "score": round(s, 2)})
    # prefer a column that actually contains a matched group value
    if matched_groups:
        group = matched_groups[0]["column"]
    unresolved = []
    if metric is None:
        unresolved.append("metric")
    if group is None:
        unresolved.append("group")
    if goal is None:
        unresolved.append("goal")
    constraints = {}
    if "budget" in lower:
        constraints["budget"] = "mentioned"
    if any(w in lower for w in ("next month", "by friday", "deadline", "asap", "urgent")):
        constraints["time"] = "mentioned"
    audience = "HR" if "hr" in lower else ("finance" if "finance" in lower else "leadership")
    return {
        "problem": text or "Decision",
        "goal": goal,
        "metric": metric,
        "group": group,
        "constraints": constraints,
        "audience": audience,
        "mode": "rules",
        "confidence": round(max(metric_score, group_score), 2) if (metric or group) else 0.0,
        "matched_columns": [c for c in (metric, group) if c],
        "matched_groups": matched_groups,
        "unresolved": unresolved,
    }
