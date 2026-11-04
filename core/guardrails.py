"""Guardrails for input, options, decision, output and audit."""
RATINGS = ("impact", "cost", "risk", "speed")


def validate_input(df, user_text):
    findings = []
    if df is None or len(df) == 0:
        findings.append({"code": "EMPTY_DATA", "message": "The dataset is empty.", "severity": "error"})
    if not (user_text or "").strip():
        findings.append({"code": "EMPTY_TEXT", "message": "No problem statement was provided.", "severity": "error"})
    return findings


def validate_options(options):
    findings = []
    if not options:
        findings.append({"code": "NO_OPTIONS", "message": "No options were generated.", "severity": "error"})
        return findings
    if len(options) != 3:
        findings.append({"code": "OPTION_COUNT", "message": f"Expected 3 options, got {len(options)}.", "severity": "error"})
    names = [str(o.get("name", "")) for o in options]
    if len(set(names)) != len(names):
        findings.append({"code": "DUPLICATE_OPTIONS", "message": "Option names must be distinct.", "severity": "error"})
    for o in options:
        for k in RATINGS:
            try:
                v = int(o.get(k, 0))
            except (TypeError, ValueError):
                v = 0
            if not (1 <= v <= 5):
                findings.append({"code": "RATING_RANGE",
                                 "message": f"{o.get('name')}: {k}={o.get(k)} is outside 1-5.",
                                 "severity": "error"})
    return findings


def validate_decision(options, best):
    findings = []
    if not options:
        findings.append({"code": "NO_OPTIONS", "message": "No options available for a decision.", "severity": "error"})
    elif not (0 <= best < len(options)):
        findings.append({"code": "BAD_BEST", "message": "Best index is out of range.", "severity": "error"})
    return findings


def validate_output(plan):
    findings = []
    if not plan:
        findings.append({"code": "NO_SLIDES", "message": "The deck has no slides.", "severity": "error"})
    return findings


def audit(session):
    """Collect guardrail findings from a session dict."""
    findings = list(session.get("findings") or [])
    findings += validate_input(session.get("df"), session.get("user_text"))
    findings += validate_options(session.get("options"))
    if session.get("options"):
        findings += validate_decision(session.get("options"), session.get("best"))
    findings += validate_output(session.get("plan"))
    return findings
