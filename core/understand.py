"""Understand the data (stage 1) and the user's situation (stage 2)."""
import json
import re
from core import research


def profile_data(df):
    """Profile a dataframe: rows, columns, types, missing %, duplicates, numeric ranges, outliers, groups."""
    profile = {
        "rows": int(len(df)),
        "columns": {},
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric": {},
        "categories": {},
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
    return profile


def guess_columns(df, profile):
    """Rule-based guess of the metric and group columns."""
    numeric = list(profile["numeric"].keys())
    categories = list(profile["categories"].keys())
    return {"metric": numeric[0] if numeric else None,
            "group": categories[0] if categories else None}


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
    return {
        "about": f"Dataset with {profile['rows']} rows and {len(columns)} columns.",
        "columns": {c: profile["columns"][c]["type"] for c in columns},
        "quality_notes": notes[:3],
        "suggested_metric": guess["metric"],
        "suggested_group": guess["group"],
        "profile": profile,
        "mode": "rules",
    }


def understand_user(text, columns, cfg, use_ai):
    """Extract problem, goal, metric, group, constraints and audience from plain words."""
    text = (text or "").strip()
    if use_ai and research.available(cfg):
        try:
            prompt = (
                "Extract the user's intent from the text. Return JSON with keys: "
                "{\"problem\": short problem statement, \"goal\": \"increase\" or \"reduce\", "
                "\"metric\": one of the column names or null, \"group\": one of the column names or null, "
                "\"constraints\": {\"budget\": string or null, \"time\": string or null}, "
                "\"audience\": string}.\n\n"
                f"Columns: {columns}\nText: {text}"
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
            }
        except Exception:
            pass
    lower = text.lower()

    def column_matches(col):
        words = [w for w in re.split(r"[_\s]+", col.lower()) if len(w) > 2]
        return any(w in lower for w in words)

    goal = "reduce" if any(w in lower for w in ("reduce", "cut", "lower", "decrease", "too much", "too high", "less")) else (
        "increase" if any(w in lower for w in ("increase", "grow", "raise", "improve", "more", "higher")) else "reduce")
    metric = next((c for c in columns if column_matches(c)), None)
    group = next((c for c in columns if c != metric and column_matches(c)), None)
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
    }
