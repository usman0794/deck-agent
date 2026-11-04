# Test Plan — Research & Tough Thinking

This plan describes the data to create and the questions to ask so you can exercise the agent's reasoning, research and clarifying-question behaviour.

---

## 1. Goal

Test that the agent:

- Understands ambiguous, incomplete or conflicting data.
- Asks only the questions it needs, and never repeats them.
- Classifies the problem type correctly.
- Researches externally and cites verified sources.
- Explains trade-offs, confidence and “why not the others”.

---

## 2. Data to create

Create these as CSV files (or JSON) and upload them in the **Data** step.

### 2.1 Ambiguous metric — `ambiguous.csv`

Two plausible metrics and a group column.

```csv
group,metric_a,metric_b
A,120,45
B,98,60
C,150,30
D,80,70
E,110,50
```

**Purpose:** the agent should ask which metric is primary, or pick one and state the assumption.

### 2.2 Missing values + outlier — `messy.csv`

```csv
date,region,sales,returns
2026-01-01,North,1200,45
2026-02-01,North,1350,52
2026-03-01,North,,48
2026-01-01,South,980,60
2026-02-01,South,,75
2026-03-01,South,1050,70
2026-01-01,East,1500,30
2026-02-01,East,1620,28
2026-03-01,East,1450,35
2026-01-01,West,800,90
2026-02-01,West,850,95
2026-03-01,West,4200,88
```

**Purpose:** tests missing-value handling, outlier detection and trend.

### 2.3 No group column — `items.csv`

```csv
item,impact,cost,risk
Upgrade CRM,8,6,4
Automate invoicing,7,4,3
Open new region,9,9,8
Renovate offices,4,7,2
Launch loyalty program,6,5,5
```

**Purpose:** rows become items; the agent must choose a criterion or ask.

### 2.4 Conflicting goals — `tradeoff.csv`

```csv
option,quality,cost,speed,risk
A,9,3,4,6
B,6,8,8,2
C,7,5,5,5
D,8,6,6,4
```

**Purpose:** tests trade-off reasoning and tie handling.

### 2.5 Date + trend — `trend.csv`

```csv
month,output,defects
2026-01,820,45
2026-02,760,60
2026-03,690,80
2026-04,640,95
2026-05,580,120
```

**Purpose:** tests trend detection and diagnosis.

---

## 3. Tough reasoning questions

Use these with the matching dataset.

### Ambiguous metric

1. “Which group should we focus on?”
2. “Improve metric_a and reduce metric_b.”
3. “We can only fund one group.”

### Missing + outlier

1. “Why are returns so high?”
2. “Which region is safest to expand?”
3. “Is sales trending up or down?”

### No group

1. “Which item should we fund first?”
2. “We only have budget for two items.”
3. “Choose between Upgrade CRM and Automate invoicing.”

### Conflicting goals

1. “Pick the best option.”
2. “We need quality above 7 and cost below 6.”
3. “Which option has the best impact-to-cost ratio?”

### Trend

1. “Why is output falling?”
2. “Which month was worst?”
3. “Should we stop the current plan?”

---

## 4. Clarifying-question tests

These should return **needs_input** with at most 3 questions.

| Input | Expected |
|---|---|
| “help me” | problem, goal, metric |
| “sales are bad” | goal (increase/reduce), metric |
| “improve sales and reduce returns” | which metric is primary |
| “which group?” | goal, metric |
| “make it better” | problem, goal, metric |

After answering, the same question id must never be asked again.

---

## 5. Research questions

Use these with **Run research** on the Problem step.

| Dataset | Question | Look for |
|---|---|---|
| ambiguous | “What good practices help prioritise groups?” | verified findings, benchmarks |
| messy | “How do others handle missing sales data?” | good practices, risks |
| items | “What frameworks help prioritise projects?” | decision criteria |
| tradeoff | “How do others choose under conflicting goals?” | trade-off frameworks |
| trend | “What causes output to fall over time?” | causes, benchmarks |

Check:

- Research slide lists themes and findings with `[n]`.
- Sources slide lists every cited source.
- Every `[n]` in the deck exists in Sources.
- Skipped pages are reported in the UI.

---

## 6. Trade-off and tie tests

- **Trade-off:** “Improve metric_a and reduce metric_b” — the constraint must be named in the deck.
- **Threshold:** “Keep quality above 7 and cost below 6” — expect the threshold in the reasoning.
- **Tie:** Use `tradeoff.csv` and ask “Choose between A and B”. If they tie, the deck must say **“Human decision required”**.
- **Ratings change:** Adjust the sliders in **Options**, then **Update ratings and decide**. The winner and confidence can change.

---

## 7. Data-shape tests

| Test | How |
|---|---|
| No numeric metric | Upload a text-only CSV; expect counts |
| No group column | Upload `items.csv`; rows become items |
| Date column | Upload `trend.csv`; expect a trend statement |
| Missing values | Upload `messy.csv` (blank cells) |
| Outlier | Upload `messy.csv` (West 4200) |
| Many numeric columns | Upload `ambiguous.csv`; expect the agent to choose or ask |

---

## 8. API test flow

```powershell
$login = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/auth/login" `
  -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}'
$headers = @{ Authorization = "Bearer $($login.token)" }

$sid = (Invoke-RestMethod -Method Post -Uri "http://localhost:8000/sessions" -Headers $headers).id
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/sessions/$sid/data" `
  -Headers $headers -Form @{ file = Get-Item "examples/ambiguous.csv" }

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/sessions/$sid/problem" `
  -Headers $headers -ContentType "application/json" `
  -Body '{"text":"Which group should we focus on?"}'

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/sessions/$sid/confirm" `
  -Headers $headers -ContentType "application/json" -Body '{"edits":{}}'

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/sessions/$sid/options" `
  -Headers $headers -ContentType "application/json" -Body '{"use_ai":false}'

Invoke-RestMethod -Method Get -Uri "http://localhost:8000/sessions/$sid/decision" -Headers $headers

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/sessions/$sid/deck" -Headers $headers
Invoke-WebRequest -Uri "http://localhost:8000/sessions/$sid/deck.pptx" -Headers $headers -OutFile "test.pptx"
```

Check: `POST /deck` returns `deck_ready`, then `GET /deck.pptx` returns a valid PPTX.

---

## 9. What “good” looks like

- The agent asks only about missing required fields, never repeats a question.
- The deck has up to 18 slides, one message per slide.
- Sources are deduplicated and numbered; every `[n]` resolves.
- The recommendation names the runner-up and why not the others.
- Confidence reflects the sensitivity scenarios and evidence strength.
- The deck says “No external research used” when research is off or unavailable.
- Reloading the page keeps your step and session.
