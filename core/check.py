"""Check the final choice: sensitivity, critique and confidence (stage 4)."""
import re
from core import research


# Six weight scenarios: user's weights, equal, and four single-criterion-heavy sets.
SCENARIOS = [
    ("Your weights", None),
    ("Equal weights", {"impact": 0.25, "cost": 0.25, "risk": 0.25, "speed": 0.25}),
    ("Impact-heavy", {"impact": 0.6, "cost": 0.15, "risk": 0.15, "speed": 0.1}),
    ("Cost-heavy", {"impact": 0.15, "cost": 0.6, "risk": 0.15, "speed": 0.1}),
    ("Risk-heavy", {"impact": 0.15, "cost": 0.15, "risk": 0.6, "speed": 0.1}),
    ("Speed-heavy", {"impact": 0.15, "cost": 0.15, "risk": 0.1, "speed": 0.6}),
]


def sensitivity(options, weights=None):
    """Re-score under 6 scenarios and count how many each option wins."""
    from core import decide  # lazy import avoids a circular dependency
    base_weights = weights or decide.WEIGHTS
    scenarios = []
    wins = {i: 0 for i in range(len(options))}
    for name, w in SCENARIOS:
        scenario_weights = w or base_weights
        scored = decide.score_options(options, scenario_weights)
        winner = decide.pick_best(scored)
        wins[winner] += 1
        scenarios.append({
            "name": name,
            "winner": options[winner]["name"],
            "score": scored[winner]["score"],
        })
    return {"scenarios": scenarios, "wins": wins, "total": len(SCENARIOS)}


def critique(topic, result, options, best, cfg, use_ai):
    """Challenge the winner: AI concerns, or rule-based flags."""
    winner = options[best]
    runner = max((o for i, o in enumerate(options) if i != best), key=lambda o: o["score"])
    if use_ai and research.available(cfg):
        try:
            prompt = (
                f"Problem: {topic}\nWinner: {winner['name']}\nSummary: {winner['summary']}\n"
                f"Ratings: impact {winner['impact']}, cost {winner['cost']}, "
                f"risk {winner['risk']}, speed {winner['speed']}\n"
                "Challenge this recommendation. Return JSON: {\"concerns\": [up to 3 short concerns]}."
            )
            data = research.complete_json(prompt, cfg)
            concerns = [str(x).strip() for x in data.get("concerns", []) if str(x).strip()][:3]
            if concerns:
                return {"concerns": concerns, "mode": "ai"}
        except Exception:
            pass
    concerns = []
    match = re.search(r"(\d+(?:\.\d+)?)%", str(winner.get("est_effect", "")))
    if match and float(match.group(1)) < 3:
        concerns.append(f"Estimated effect ({winner.get('est_effect')}) is under 3% of the total.")
    if winner.get("risk", 0) >= 4:
        concerns.append(f"Risk rating is {winner['risk']}/5.")
    margin = winner.get("score", 0) - runner.get("score", 0)
    if margin < 0.2:
        concerns.append(f"Margin over the runner-up is only {margin:.2f}.")
    return {"concerns": concerns, "mode": "rules"}


def confidence(sensitivity_result, options, best, evidence_strength=0, has_research=False):
    """Label confidence from the sensitivity wins; cap at Medium without verified evidence."""
    wins = sensitivity_result["wins"]
    total = sensitivity_result["total"]
    count = wins.get(best, 0)
    label = "High" if count >= 5 else "Medium" if count >= 3 else "Low"
    if has_research and evidence_strength == 0 and label == "High":
        label = "Medium"
    alternative = None
    if label == "Low":
        others = [i for i in wins if i != best]
        if others:
            runner = max(others, key=lambda i: wins[i])
            alternative = options[runner]["name"]
    return {"label": label, "wins": count, "total": total, "alternative": alternative,
            "evidence_strength": evidence_strength}


def why_not_others(options, best):
    """Code-generated 'why not' text for each rejected option."""
    winner = options[best]
    texts = {}
    for i, o in enumerate(options):
        if i == best:
            continue
        diffs = []
        if winner["impact"] > o["impact"]:
            diffs.append("impact")
        if winner["cost"] < o["cost"]:
            diffs.append("lower cost")
        if winner["risk"] < o["risk"]:
            diffs.append("lower risk")
        if winner["speed"] > o["speed"]:
            diffs.append("speed")
        texts[str(i)] = f"{o['name']} loses on {', '.join(diffs) or 'overall balance'}."
    return texts


def is_tie(scored, best=None):
    """True when the top two scores are equal."""
    if len(scored) < 2:
        return False
    ordered = sorted(range(len(scored)), key=lambda i: scored[i]["score"], reverse=True)
    return abs(scored[ordered[0]]["score"] - scored[ordered[1]]["score"]) < 1e-9
