"""Problem type classification (rules first, AI-assisted when available)."""
from core import research

TYPES = ["improve", "prioritise", "allocate", "diagnose", "choose"]


def classify_problem(text, cfg=None, use_ai=False):
    """Return {type, confidence, reason, mode} for the user's problem statement."""
    text = (text or "").strip()
    if use_ai and research.available(cfg):
        try:
            prompt = (
                "Classify the user's problem statement into exactly one type: "
                "improve (increase/reduce a metric), prioritise (which group/item first), "
                "allocate (where budget/staff/effort should go), diagnose (why a metric is high/low), "
                "choose (pick the best among named items). "
                "Return JSON: {\"type\": one of the types, \"confidence\": 0-1, \"reason\": short string}.\n\n"
                f"Text: {text}"
            )
            data = research.complete_json(prompt, cfg)
            t = data.get("type")
            if isinstance(t, str):
                t = t.strip().lower()
                mapping = {"reduce": "improve", "increase": "improve",
                           "prioritize": "prioritise", "priorise": "prioritise",
                           "allocation": "allocate", "diagnosis": "diagnose",
                           "choice": "choose"}
                t = mapping.get(t, t)
            if t in TYPES:
                try:
                    conf = float(data.get("confidence", 0.7))
                except (TypeError, ValueError):
                    conf = 0.7
                return {"type": t, "confidence": max(0.0, min(1.0, conf)),
                        "reason": str(data.get("reason", "")).strip(), "mode": "ai"}
        except Exception:
            pass
    lower = text.lower()
    if any(w in lower for w in ("why", "reason", "cause", "explain", "driving", "what's behind", "what is behind")):
        return {"type": "diagnose", "confidence": 0.85, "reason": "asks why", "mode": "rules"}
    if any(w in lower for w in ("first", "priority", "prioritise", "prioritize", "fix first", "deal with first")):
        return {"type": "prioritise", "confidence": 0.8, "reason": "asks what to do first", "mode": "rules"}
    if any(w in lower for w in ("which", "best", "pick", "choose", "compare", "top")):
        return {"type": "choose", "confidence": 0.8, "reason": "asks which/best", "mode": "rules"}
    if any(w in lower for w in ("where should", "budget", "allocate", "spend", "invest", "distribute")):
        return {"type": "allocate", "confidence": 0.8, "reason": "asks where to allocate", "mode": "rules"}
    if any(w in lower for w in ("increase", "reduce", "improve", "raise", "lower", "cut", "grow", "save", "higher", "less", "too much", "too high", "need a plan", "plan")):
        return {"type": "improve", "confidence": 0.75, "reason": "asks to change a metric", "mode": "rules"}
    return {"type": "improve", "confidence": 0.3, "reason": "no clear signal", "mode": "rules"}
