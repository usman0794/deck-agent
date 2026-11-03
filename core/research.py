"""Optional AI step. Drafts short context and actions via an OpenAI-compatible API.

Supports Groq and LongCat. Pick the provider with AI_PROVIDER in .env
(groq or longcat) and set the matching API key and model. It does NOT browse
the web: treat the output as a draft and verify it before presenting."""
import json
import os
import re

# name -> (API key env var, OpenAI-compatible base URL)
PROVIDERS = {
    "groq": {
        "key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    "longcat": {
        "key_env": "LONGCAT_API_KEY",
        "base_url": "https://api.longcat.chat/openai/v1",
    },
}


def _provider():
    name = (os.getenv("AI_PROVIDER") or "").strip().lower()
    if not name:
        return None, None
    if name not in PROVIDERS:
        raise RuntimeError(f"Unknown AI_PROVIDER={name!r}. Use 'groq' or 'longcat'.")
    return name, PROVIDERS[name]


def api_key(cfg=None):
    _, provider = _provider()
    return (os.getenv(provider["key_env"]) or "").strip() if provider else ""


def available(cfg=None):
    return bool(api_key(cfg)) and bool(model_name())


def model_name():
    """Model comes from .env: GROQ_MODEL or LONGCAT_MODEL."""
    _, provider = _provider()
    if not provider:
        return None
    prefix = provider["key_env"].removesuffix("_API_KEY")
    return (os.getenv(f"{prefix}_MODEL") or "").strip() or None


def research(topic, summary_lines, cfg=None):
    name, provider = _provider()
    if not provider:
        raise RuntimeError(
            "Set AI_PROVIDER in the .env file (groq or longcat) to use the AI step."
        )
    key = api_key(cfg)
    if not key:
        raise RuntimeError(
            f"Set {provider['key_env']} in the .env file to use the AI step "
            f"(AI_PROVIDER={name})."
        )
    model = model_name()
    if not model:
        raise RuntimeError(
            f"Set {provider['key_env'].removesuffix('_API_KEY')}_MODEL in the .env file "
            f"for provider '{name}'."
        )
    from openai import OpenAI

    client = OpenAI(api_key=key, base_url=provider["base_url"])
    prompt = (
        f"Topic: {topic}\nData summary:\n- " + "\n- ".join(summary_lines) + "\n\n"
        "Return ONLY a JSON object: {\"background\": [up to 3 short context bullets], "
        "\"actions\": [up to 4 short, concrete recommended actions]}. "
        "Do not invent statistics, quotes or citations. Each bullet under 18 words."
    )
    resp = client.chat.completions.create(
        model=model,
        max_tokens=int(os.getenv("AI_MAX_TOKENS", "2000")),
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.choices[0].message.content or ""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise RuntimeError(f"{name} did not return JSON: {text[:200]}")
    data = json.loads(match.group(0))
    clean = lambda xs: [str(x).strip() for x in xs if str(x).strip()]
    return {"background": clean(data.get("background", []))[:3], "actions": clean(data.get("actions", []))[:4]}


def ai_options(problem, goal, metric, category, cfg=None):
    """Ask the AI for exactly 3 options as JSON. Retries once on invalid output.

    Uses the same provider/key/model settings as research(); key handling is unchanged.
    """
    name, provider = _provider()
    if not provider:
        raise RuntimeError(
            "Set AI_PROVIDER in the .env file (groq or longcat) to use AI options."
        )
    key = api_key(cfg)
    if not key:
        raise RuntimeError(
            f"Set {provider['key_env']} in the .env file to use AI options "
            f"(AI_PROVIDER={name})."
        )
    model = model_name()
    if not model:
        raise RuntimeError(
            f"Set {provider['key_env'].removesuffix('_API_KEY')}_MODEL in the .env file "
            f"for provider '{name}'."
        )
    from openai import OpenAI

    client = OpenAI(api_key=key, base_url=provider["base_url"])
    prompt = (
        f"Problem: {problem}\nGoal: {goal} {metric}\nGroup column: {category}\n\n"
        "Propose exactly 3 different, realistic options to solve the problem. "
        "Return ONLY a JSON array of 3 objects with keys: name, summary, est_effect, "
        "impact, cost, risk, speed. impact/cost/risk/speed are integers 1-5 "
        "(5 = highest impact, highest cost, highest risk, fastest)."
    )
    last_err = None
    for _ in range(2):  # initial attempt + one retry
        try:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=int(os.getenv("AI_MAX_TOKENS", "2000")),
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.choices[0].message.content or ""
            match = re.search(r"\[.*\]", text, re.S)
            if not match:
                raise ValueError("no JSON array found")
            data = json.loads(match.group(0))
            if not isinstance(data, list) or len(data) != 3:
                raise ValueError(
                    f"expected 3 options, got {len(data) if isinstance(data, list) else type(data).__name__}"
                )
            options = []
            for item in data:
                options.append({
                    "name": str(item.get("name", "")).strip(),
                    "summary": str(item.get("summary", "")).strip(),
                    "est_effect": item.get("est_effect", ""),
                    "impact": int(item.get("impact", 3)),
                    "cost": int(item.get("cost", 3)),
                    "risk": int(item.get("risk", 3)),
                    "speed": int(item.get("speed", 3)),
                })
            return options
        except Exception as e:
            last_err = e
    raise RuntimeError(f"AI did not return 3 valid options after retry: {last_err}")

