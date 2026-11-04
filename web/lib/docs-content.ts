export interface DocsPageContent {
  title: string;
  description: string;
  content: string;
}

export const docsContent: Record<string, DocsPageContent> = {
  overview: {
    title: "What is Briefing Deck Agent?",
    description: "Turn raw data into an evidence-backed decision deck.",
    content: `# What is Briefing Deck Agent?

Briefing Deck Agent is a local tool that turns raw data into an evidence-backed decision deck. You upload a CSV, Excel or JSON file (or scrape a web table), describe the problem in plain words, optionally research it externally, and get three solutions, a recommendation, and a detailed PowerPoint.

## What it does

- **Understands your data** — detects a numeric metric and a grouping column, or treats rows as items.
- **Understands your problem** — classifies it as improve, prioritise, allocate, diagnose or choose.
- **Researches externally** — searches the web, fetches pages safely, verifies snippets and groups findings.
- **Recommends** — three domain-neutral solutions, weighted scoring, 6-scenario sensitivity and confidence.
- **Explains** — a deck with sources, speaker notes, roadmap, risks and KPIs.

## How it works

1. **Data** — upload a file or scrape a web table.
2. **Problem** — describe the situation; confirm what the agent understood.
3. **Research** — optional web research for good practices, causes, benchmarks and risks.
4. **Options** — three evidence-backed solutions with ratings; adjust ratings if needed.
5. **Decision** — confidence, recommendation, why-not-the-others, and the downloadable deck.

## Architecture

\`\`\`
web/       Next.js + Tailwind CSS + shadcn/ui frontend
api/       FastAPI backend (sessions, research, decks)
service/   UI-independent session workflow
core/      pure logic (data, understand, decide, check, plan, build, research, auth)
cli.py     offline command line (no UI)
\`\`\`

The frontend and backend are separate apps. The API contract in \`docs/api_contract.md\` is the boundary.

## Where it runs

- **Frontend** — http://localhost:3000
- **API** — http://localhost:8000 (Swagger UI at \`/docs\`)
- **CLI** — any terminal, no UI or sign-in

## Next steps

1. [Getting Started](/docs/getting-started) — install and run the app.
2. [Configuration](/docs/configuration) — keys, users and slide settings.
3. [Deep Research](/docs/research) — how external research works.
`,
  },

  "getting-started": {
    title: "Getting Started",
    description: "Install and run the backend and frontend.",
    content: `# Getting Started

## 1. Backend

\`\`\`powershell
pip install -r requirements.txt
copy .env.example .env      # then edit .env with your keys (Windows)
cp .env.example .env        # macOS/Linux
uvicorn api.main:app --reload
\`\`\`

API docs: http://localhost:8000/docs

## 2. Frontend

\`\`\`powershell
cd web
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
\`\`\`

Open http://localhost:3000.

## 3. Your first deck

1. Sign in with \`admin\` / \`admin123\` (change it before real use).
2. **Data** — upload \`workers_sample_data.csv\` or another CSV.
3. **Problem** — type e.g. \`we pay too much overtime and HR needs a plan next month\`.
4. Click **Understand**, check what the agent understood, then **Confirm and continue**.
5. **Research** — run it, or skip it.
6. **Options** — adjust ratings if you want, then **Update ratings and decide**.
7. **Decision** — click **Download briefing.pptx**.

## Demo login

\`\`\`powershell
python manage_users.py add yourname
python manage_users.py remove admin
\`\`\`

Or edit \`access.json\` directly. See [Configuration](/docs/configuration).

## CLI (no UI)

\`\`\`powershell
python cli.py data.csv --text "we pay too much overtime and HR needs a plan next month" --out briefing.pptx
\`\`\`

## Next

- [Configuration](/docs/configuration)
- [Data Input](/docs/data-input)
`,
  },

  configuration: {
    title: "Configuration",
    description: "Keys, users, slides and research settings.",
    content: `# Configuration

## \`.env\`

Loaded automatically at startup by \`core/__init__.py\`. Real environment variables take precedence over \`.env\`.

\`\`\`ini
GROQ_API_KEY=
LONGCAT_API_KEY=

# groq or longcat (required — there is no built-in default)
AI_PROVIDER=groq

# Model for each provider (required for the AI step)
GROQ_MODEL=openai/gpt-oss-120b
LONGCAT_MODEL=LongCat-2.0

# Optional
AI_MAX_TOKENS=2000
SESSION_DAYS=7
# APP_SECRET=replace-with-a-long-random-string
\`\`\`

## \`config.json\`

\`\`\`json
{
  "organisation": "Your Organisation",
  "theme": { "primary": "01411C" },
  "slides": {
    "executive_summary": true, "problem": true, "data": true, "chart": true,
    "research": true, "good_practices": true, "solutions": true, "comparison": true,
    "criteria": true, "scores": true, "robustness": true, "recommendation": true,
    "roadmap": true, "risks": true, "kpis": true, "sources": true,
    "key_figures": false, "table": false
  },
  "max_slides": 18,
  "max_chart_items": 6,
  "table_rows": 8,
  "table_cols": 6,
  "search": { "provider": "ddgs", "env_var": "SEARCH_API_KEY", "base_url": "https://api.example.com/search" },
  "research": { "max_seconds": 120, "max_model_calls": 25, "max_queries": 6, "max_pages": 10, "max_results": 5, "cache_dir": "cache" }
}
\`\`\`

| Key | Meaning |
|---|---|
| \`organisation\` | Default organisation on the title slide |
| \`theme.primary\` | Hex colour for titles and charts |
| \`slides.*\` | Toggle each slide; \`max_slides\` caps the deck at 18 |
| \`search.provider\` | \`ddgs\` (no key) or \`key\` (key-based provider) |
| \`research.*\` | Time, model-call, query and page limits |

## Users

Edit \`access.json\`:

\`\`\`json
{
  "users": {
    "admin": { "password": "admin123", "role": "admin" },
    "viewer": { "password": "view123", "role": "viewer" }
  }
}
\`\`\`

- \`admin\` — full access, including AI and research.
- \`viewer\` — can load data, plan and download the deck, but not use AI or research.

\`manage_users.py\` writes PBKDF2 hashes to \`users.json\`; both files can coexist.

## Next

- [AI Providers](/docs/ai-providers)
- [Security & Privacy](/docs/security)
`,
  },

  "data-input": {
    title: "Data Input",
    description: "Upload files or scrape a web table.",
    content: `# Data Input

## Upload a file

Supported types: \`.csv\`, \`.xlsx\`, \`.xls\`, \`.json\`.

- CSV parsing sniffs the delimiter (\`,\`, \`;\`, tab, \`|\`) and skips ragged rows.
- Excel and JSON are loaded directly.
- The preview shows the first rows; you can download the loaded data as CSV.

## Scrape a web page

Enter a URL and choose what to extract:

| Preset | Selector | Use for |
|---|---|---|
| Table rows | \`table tr\` | Real HTML tables |
| Section headings | \`h2\` | Page sections |
| Lists and cards | \`li\` | List items |
| Paragraphs | \`p\` | Paragraph text |
| Custom selector… | your own CSS | Anything else |

- URLs without a scheme get \`https://\` added.
- If the selector matches nothing, the scraper extracts headings, paragraphs and list items into an \`element\` / \`text\` table.
- Pages with almost no HTML are likely JavaScript-rendered; the scraper tells you it cannot run JavaScript.

## Data shapes

The analysis degrades gracefully:

- **No numeric column** — uses counts per group.
- **No group column** — treats rows as items.
- **Date column** — adds a trend check (up, down or flat) to the data summary.
- **Unfamiliar schema** — uses a smaller analysis and says so.

## Next

- [Problem & Understanding](/docs/problem)
- [Deck & Downloads](/docs/deck)
`,
  },

  problem: {
    title: "Problem & Understanding",
    description: "How the agent interprets plain words.",
    content: `# Problem & Understanding

## Problem types

The agent classifies your text into one primary type:

| Type | Meaning |
|---|---|
| \`improve\` | Increase or reduce a metric |
| \`prioritise\` | Which group or item to deal with first |
| \`allocate\` | Where budget, staff or effort should go |
| \`diagnose\` | Why a metric is high or low |
| \`choose\` | Pick the best among named items |

## Intent extraction

From your plain words, the agent extracts:

- **Problem** — a short statement.
- **Goal** — \`increase\` or \`reduce\`.
- **Metric** — the numeric column to move.
- **Group** — the categorical column to compare.
- **Constraints** — budget, time, audience.
- **Audience** — who will read the deck.

Words are fuzzy-matched to real column names and group values using \`difflib\`. A small generic polarity list distinguishes increase/reduce words. If the direction is unclear, the agent asks instead of assuming.

## Clarifying questions

If required fields are missing (problem, goal, metric), the agent returns \`needs_input\` with at most 3 questions. Questions use real column names or group names from your data. The same question is never asked twice; answers are merged into the intent.

## Confirmation

After extraction, the agent shows **“Here is what I understood”** with editable fields. Confirm to continue; edit first if anything is wrong.

## Next

- [Deep Research](/docs/research)
- [Options & Decision](/docs/decision)
`,
  },

  research: {
    title: "Deep Research",
    description: "External research with verified sources.",
    content: `# Deep Research

## Pipeline

1. **Plan** — 3–6 sub-questions about good practice, causes, benchmarks, risks and measurement.
2. **Search** — DuckDuckGo (\`ddgs\`, no key) or a key-based provider.
3. **Fetch** — top pages with SSRF protection, robots.txt, 10 s timeout and 1 MB cap.
4. **Extract** — the model writes up to 3 short findings per page.
5. **Verify** — a finding is kept only if its snippet really occurs in the page and shares key terms with the claim.
6. **Synthesize** — findings are grouped into causes, good practices, benchmarks and risks.

## Providers

\`\`\`json
"search": { "provider": "ddgs", "env_var": "SEARCH_API_KEY", "base_url": "https://api.example.com/search" }
\`\`\`

- \`ddgs\` needs no key.
- \`key\` reads the key from the env var named in config and calls \`GET {base_url}?q=...&limit=5\` with \`Authorization: Bearer <key>\`.

## Privacy and safety

- Queries use only the generic problem wording. Column names, group values, file names and PII-like tokens are stripped.
- Fetched pages are untrusted data. Prompt-injection phrases are flagged and the page is ignored.
- Sources are deduplicated by URL and numbered; findings reference those numbers.
- Low-quality claims (maintenance, offline, error, outage) are dropped.

## Limits and loading states

- Limits: 25 model calls, 120 s, 6 queries, 10 pages. Exceeding them returns \`partial\`.
- The UI shows a loading banner while researching, a progress bar, and any skipped pages.
- If research is unavailable, the deck says **“No external research used”** and falls back to data-only options.

## Next

- [Options & Decision](/docs/decision)
- [AI Providers](/docs/ai-providers)
`,
  },

  decision: {
    title: "Options & Decision",
    description: "Three solutions, scoring and confidence.",
    content: `# Options & Decision

## Solution archetypes

Six domain-neutral archetypes are available. The best 3 are selected from the problem type and data shape:

| Archetype | Idea |
|---|---|
| \`target_the_worst\` | Focus on the largest contributor |
| \`copy_the_best\` | Apply what the best group does |
| \`spread_evenly\` | Distribute effort evenly |
| \`quick_win_in_one_group\` | Start small for a fast win |
| \`pilot_then_scale\` | Test in one group, then scale |
| \`concentrate_on_top_contributors\` | Put most effort into the top contributors |

Options must differ in approach, not only intensity. Near-duplicates trigger one retry, then a rule fallback.

## Scoring

\`\`\`
score = impact*0.4 + (6-cost)*0.25 + (6-risk)*0.2 + speed*0.15
\`\`\`

Cost and risk are lower-is-better. Ratings are integers 1–5.

## Sensitivity and confidence

The winner is re-scored under 6 weight scenarios: your weights, equal weights, impact-heavy, cost-heavy, risk-heavy and speed-heavy.

- **High** — winner in at least 5 of 6.
- **Medium** — 3 or 4.
- **Low** — fewer than 3; the runner-up is named.

If the winner has no verified research evidence, confidence is capped at Medium.

## Ties and “why not”

If the top two scores tie, the deck says **“Human decision required”** and shows both. Every rejected option gets a code-generated “why not” line based on the score differences.

## Next

- [Deck & Downloads](/docs/deck)
- [Deep Research](/docs/research)
`,
  },

  deck: {
    title: "Deck & Downloads",
    description: "What is in the PowerPoint and how to download it.",
    content: `# Deck & Downloads

## Slides

The deck contains up to 18 slides:

1. Title
2. Executive summary
3. The problem as understood
4. What the data shows
5. Chart: metric by group
6. What outside research found
7. Good practices and benchmarks found
8. Solution 1
9. Solution 2
10. Solution 3
11. Three solutions compared
12. How we judged
13. Robustness
14. Recommendation and why
15. Implementation roadmap
16. Risks and mitigations
17. KPIs to track
18. Sources

Speaker notes carry the reasoning on slides 2, 6, 8–10, 13 and 14.

## Sources and evidence

- Sources are deduplicated by URL and numbered.
- Findings reference those numbers, e.g. \`[1]\`.
- The Sources slide lists every cited source with title, domain, retrieved date and URL.

## Download

The UI and API **build the deck before downloading**:

\`\`\`bash
curl -X POST http://localhost:8000/sessions/<id>/deck
curl -OJ http://localhost:8000/sessions/<id>/deck.pptx
\`\`\`

Calling \`GET /deck.pptx\` before \`POST /deck\` returns \`404\`.

## CLI

\`\`\`powershell
python cli.py data.csv --text "we pay too much overtime and HR needs a plan next month" --out briefing.pptx
\`\`\`

## Next

- [API Overview](/docs/api-overview)
- [Configuration](/docs/configuration)
`,
  },

  "api-overview": {
    title: "API Overview",
    description: "Base URL, authentication and errors.",
    content: `# API Overview

Base URL: \`http://localhost:8000\`. Swagger UI: \`http://localhost:8000/docs\`.

## Authentication

\`\`\`bash
curl -X POST http://localhost:8000/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username":"admin","password":"admin123"}'
\`\`\`

Response:

\`\`\`json
{"token": "...", "user": "admin", "role": "admin"}
\`\`\`

Send \`Authorization: Bearer <token>\` on all other endpoints. Auth is pluggable; set \`auth_required\` in \`config.json\` to enforce it.

## Errors

\`\`\`json
{"code": "ERROR_CODE", "message": "Human readable message", "findings": []}
\`\`\`

## Health

\`\`\`bash
curl http://localhost:8000/health
\`\`\`

Response: \`{"status": "ok"}\`.

## Models

\`\`\`bash
curl http://localhost:8000/v1/models
\`\`\`

Returns the configured AI model and provider.

## Session states

\`\`\`
created → data_loaded → needs_input | understood → researched → options_ready → decided → deck_ready
                └────────────────────→ blocked
\`\`\`

## Next

- [API Authentication](/docs/api-auth)
- [API Sessions](/docs/api-sessions)
`,
  },

  "api-auth": {
    title: "API Authentication",
    description: "Login and bearer tokens.",
    content: `# API Authentication

## POST /auth/login

Exchange a username and password for a bearer token.

\`\`\`bash
curl -X POST http://localhost:8000/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username":"admin","password":"admin123"}'
\`\`\`

Response:

\`\`\`json
{"token": "...", "user": "admin", "role": "admin"}
\`\`\`

## Using the token

\`\`\`bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/sessions
\`\`\`

Tokens are created with the existing \`core.auth\` module (\`auth.make_token(username)\`); no auth logic is duplicated.

## Roles

- \`admin\` — full access, including AI and research.
- \`viewer\` — can load data, plan and download the deck, but not use AI or research.

## Next

- [API Sessions](/docs/api-sessions)
`,
  },

  "api-sessions": {
    title: "API Sessions",
    description: "The session lifecycle and endpoints.",
    content: `# API Sessions

## Create a session

\`\`\`bash
curl -X POST http://localhost:8000/sessions
\`\`\`

## Upload data

\`\`\`bash
curl -X POST http://localhost:8000/sessions/<id>/data \\
  -F "file=@workers_sample_data.csv"
\`\`\`

## Scrape data

\`\`\`bash
curl -X POST http://localhost:8000/sessions/<id>/scrape \\
  -F "url=https://www.w3schools.com/html/html_tables.asp" \\
  -F "selector=table tr"
\`\`\`

## Submit the problem

\`\`\`bash
curl -X POST http://localhost:8000/sessions/<id>/problem \\
  -H "Content-Type: application/json" \\
  -d '{"text":"we pay too much overtime and need a plan"}'
\`\`\`

## Answer questions

\`\`\`bash
curl -X POST http://localhost:8000/sessions/<id>/answers \\
  -H "Content-Type: application/json" \\
  -d '{"answers":{"goal":"reduce","metric":"overtime_hours"}}'
\`\`\`

## Confirm

\`\`\`bash
curl -X POST http://localhost:8000/sessions/<id>/confirm \\
  -H "Content-Type: application/json" \\
  -d '{"edits":{"metric":"overtime_hours"}}'
\`\`\`

## Options and ratings

\`\`\`bash
curl -X POST http://localhost:8000/sessions/<id>/options \\
  -H "Content-Type: application/json" -d '{"use_ai":false}'

curl -X PATCH http://localhost:8000/sessions/<id>/ratings \\
  -H "Content-Type: application/json" \\
  -d '{"option_ratings":{"0":{"impact":5,"cost":1,"risk":1,"speed":5}}}'
\`\`\`

## Decision and deck

\`\`\`bash
curl http://localhost:8000/sessions/<id>/decision
curl -X POST http://localhost:8000/sessions/<id>/deck
curl -OJ http://localhost:8000/sessions/<id>/deck.pptx
\`\`\`

## Next

- [API Research](/docs/api-research)
- [API Overview](/docs/api-overview)
`,
  },

  "api-research": {
    title: "API Research",
    description: "External research endpoints.",
    content: `# API Research

## POST /sessions/{id}/research

Run external deep research (search, fetch, extract, verify).

\`\`\`bash
curl -X POST http://localhost:8000/sessions/<id>/research
\`\`\`

Response:

\`\`\`json
{
  "status": "ok",
  "themes": {"causes": ["F1"], "good_practices": ["F2"], "benchmarks": [], "risks": []},
  "findings": [{"id": "F1", "claim": "...", "source_url": "https://...", "title": "...", "retrieved_date": "2026-11-04", "supporting_snippet": "..."}],
  "sources": [{"number": 1, "title": "...", "url": "https://...", "retrieved_date": "2026-11-04"}],
  "coverage": 1.0,
  "message": "",
  "kept": 4,
  "dropped": 2,
  "model_calls": 3,
  "page_errors": []
}
\`\`\`

- Sources are deduplicated by URL and numbered.
- \`page_errors\` lists pages skipped by robots.txt, timeouts or HTTP errors.
- If research is unavailable or partial, the deck says so and falls back to data-only options.

## GET /sessions/{id}/sources

\`\`\`bash
curl http://localhost:8000/sessions/<id>/sources
\`\`\`

Response:

\`\`\`json
{"status": "researched", "sources": [{"number": 1, "title": "...", "url": "https://...", "retrieved_date": "2026-11-04"}]}
\`\`\`

## Next

- [Deep Research](/docs/research)
- [AI Providers](/docs/ai-providers)
`,
  },

  "ai-providers": {
    title: "AI Providers",
    description: "Groq, LongCat and search providers.",
    content: `# AI Providers

## AI model (Groq or LongCat)

\`\`\`ini
AI_PROVIDER=groq            # or longcat
GROQ_API_KEY=...
LONGCAT_API_KEY=...
GROQ_MODEL=openai/gpt-oss-120b
LONGCAT_MODEL=LongCat-2.0
\`\`\`

- \`AI_PROVIDER\` is required; there is no built-in default.
- AI calls time out after 30 s.
- Every AI step has a rule-based fallback.

## Search provider

\`\`\`json
"search": { "provider": "ddgs", "env_var": "SEARCH_API_KEY", "base_url": "https://api.example.com/search" }
\`\`\`

| Provider | Key | Notes |
|---|---|---|
| \`ddgs\` | No | DuckDuckGo via the \`ddgs\` package |
| \`key\` | Yes | Generic JSON search API; key read from the env var named in config |

The \`key\` provider calls \`GET {base_url}?q=...&limit=5\` with \`Authorization: Bearer <key>\` and expects \`{"results": [{ "title", "url", "snippet" }]}\`.

## Adding a provider

To use a different search engine, set \`provider: "key"\`, point \`base_url\` at their endpoint, and add the key to \`.env\` under the name in \`env_var\`. Adapt \`KeySearchProvider.search()\` if their auth header or response shape differs.

## Next

- [Deep Research](/docs/research)
- [Security & Privacy](/docs/security)
`,
  },

  security: {
    title: "Security & Privacy",
    description: "Keys, PII, SSRF and sessions.",
    content: `# Security & Privacy

## Secrets

- \`.env\`, \`.auth_secret\`, \`access.json\`, \`users.json\`, \`cache/\`, \`sessions/\`, \`session_data/\` and generated \`.pptx\` files should not be committed.
- \`access.json\` holds plain passwords; \`users.json\` holds PBKDF2 hashes.
- Session cookies are HMAC-signed and expiring.

## Research privacy

- Queries use only the generic problem wording. Column names, group values, file names and PII-like tokens are stripped.
- Fetched pages are untrusted data. Prompt-injection phrases are flagged and the page is ignored.
- Sources are deduplicated and numbered; findings reference those numbers.
- The scraper blocks private/local IPs (SSRF), respects \`robots.txt\`, and honours timeouts and size caps.

## Production

- Put the API behind HTTPS and consider SSO.
- Set \`auth_required\` in \`config.json\` if the API is exposed.
- Keep \`.env\` out of the repository and the offline artefacts.

## Next

- [Configuration](/docs/configuration)
- [FAQ & Troubleshooting](/docs/faq)
`,
  },

  faq: {
    title: "FAQ & Troubleshooting",
    description: "Common problems and fixes.",
    content: `# FAQ & Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| Login screen keeps appearing | Cookie not set / \`.auth_secret\` changed | Restart the API and sign in again |
| AI options disabled | Missing provider, key, or model | Check \`.env\`: \`AI_PROVIDER\`, \`GROQ_API_KEY\`/\`LONGCAT_API_KEY\`, \`GROQ_MODEL\`/\`LONGCAT_MODEL\` |
| \`ModuleNotFoundError\` | Dependencies not installed | \`pip install -r requirements.txt\` / \`npm install\` in \`web/\` |
| Scrape says "no table" | Page has no \`<table>\` | Use \`h2\`, \`li\`, or accept the page-text fallback |
| Scrape returns almost nothing | Page is JavaScript-rendered | Use the site's export/API or copy the data |
| CSV tokenizing error | Wrong delimiter or ragged rows | The loader sniffs delimiters and skips bad rows |
| Downloaded \`briefing.pptx\` won't open | \`GET /deck.pptx\` before \`POST /deck\` | The UI builds first; via API call \`POST /sessions/{id}/deck\` before downloading |
| Research shows \`partial\` / skipped pages | robots.txt, timeouts or HTTP 429 | Wait and retry; the deck falls back to data-only options |
| AI step hangs | Provider is slow or unreachable | AI calls time out after 30 s and fall back to rules |
| Port already in use | Another API/frontend process | Stop it or run with \`--port 8001\` / \`-p 3001\` |

## Next

- [Deck & Downloads](/docs/deck)
- [Developer Guide](/docs/developer-guide)
`,
  },

  "developer-guide": {
    title: "Developer Guide",
    description: "Architecture, modules and tests.",
    content: `# Developer Guide

## Layout

\`\`\`
web/       Next.js + Tailwind CSS + shadcn/ui frontend
api/       FastAPI backend
service/   UI-independent session workflow
core/      pure logic (data, understand, decide, check, plan, build, research, auth)
cli.py     offline command line
docs/      this documentation
\`\`\`

## Core modules

| Module | Responsibility |
|---|---|
| \`core/analyze.py\` | Metric/category detection and summary statistics |
| \`core/understand.py\` | Data profiling and intent extraction |
| \`core/problem.py\` | Problem-type classification |
| \`core/archetypes.py\` | Domain-neutral solution archetypes |
| \`core/decide.py\` | Option generation, scoring and recommendation |
| \`core/check.py\` | Sensitivity, critique, confidence |
| \`core/plan.py\` | Deck slide structure |
| \`core/build.py\` | PowerPoint generation |
| \`core/research.py\` | AI provider selection and JSON calls |
| \`core/research_web.py\` | Deep research: plan, search, fetch, extract, verify, synthesize |
| \`core/guardrails.py\` | Input, option, decision, output and audit checks |
| \`core/auth.py\` | Users, tokens, sessions |

## Service and API

- \`service/session.py\` — session model and stores (memory / file).
- \`service/workflow.py\` — session workflow functions.
- \`api/main.py\` — FastAPI endpoints.

## Tests

\`\`\`powershell
pytest
\`\`\`

Tests cover problem types, data shapes, vague-text questions, banned words, service flow, API flow, ratings updates, file-store persistence and research behaviour with mocks.

## Adding a docs page

1. Add content to \`web/lib/docs-content.ts\`.
2. Add the page to \`web/lib/docs.ts\` navigation.
3. The route \`/docs/<slug>\` is generated automatically.

## Next

- [Overview](/docs/overview)
- [API Overview](/docs/api-overview)
`,
  },
  "test-plan": {
    title: "Test Plan",
    description: "Data schemas, tough questions and expected observations.",
    content: `# Test Plan — Research & Tough Thinking

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

### 2.1 Ambiguous metric — \`ambiguous.csv\`

Two plausible metrics and a group column.

\`\`\`csv
group,metric_a,metric_b
A,120,45
B,98,60
C,150,30
D,80,70
E,110,50
\`\`\`

**Purpose:** the agent should ask which metric is primary, or pick one and state the assumption.

### 2.2 Missing values + outlier — \`messy.csv\`

\`\`\`csv
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
\`\`\`

**Purpose:** tests missing-value handling, outlier detection and trend.

### 2.3 No group column — \`items.csv\`

\`\`\`csv
item,impact,cost,risk
Upgrade CRM,8,6,4
Automate invoicing,7,4,3
Open new region,9,9,8
Renovate offices,4,7,2
Launch loyalty program,6,5,5
\`\`\`

**Purpose:** rows become items; the agent must choose a criterion or ask.

### 2.4 Conflicting goals — \`tradeoff.csv\`

\`\`\`csv
option,quality,cost,speed,risk
A,9,3,4,6
B,6,8,8,2
C,7,5,5,5
D,8,6,6,4
\`\`\`

**Purpose:** tests trade-off reasoning and tie handling.

### 2.5 Date + trend — \`trend.csv\`

\`\`\`csv
month,output,defects
2026-01,820,45
2026-02,760,60
2026-03,690,80
2026-04,640,95
2026-05,580,120
\`\`\`

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

- Research slide lists themes and findings with \`[n]\`.
- Sources slide lists every cited source.
- Every \`[n]\` in the deck exists in Sources.
- Skipped pages are reported in the UI.

---

## 6. Trade-off and tie tests

- **Trade-off:** “Improve metric_a and reduce metric_b” — the constraint must be named in the deck.
- **Threshold:** “Keep quality above 7 and cost below 6” — expect the threshold in the reasoning.
- **Tie:** Use \`tradeoff.csv\` and ask “Choose between A and B”. If they tie, the deck must say **“Human decision required”**.
- **Ratings change:** Adjust the sliders in **Options**, then **Update ratings and decide**. The winner and confidence can change.

---

## 7. Data-shape tests

| Test | How |
|---|---|
| No numeric metric | Upload a text-only CSV; expect counts |
| No group column | Upload \`items.csv\`; rows become items |
| Date column | Upload \`trend.csv\`; expect a trend statement |
| Missing values | Upload \`messy.csv\` (blank cells) |
| Outlier | Upload \`messy.csv\` (West 4200) |
| Many numeric columns | Upload \`ambiguous.csv\`; expect the agent to choose or ask |

---

## 8. API test flow

\`\`\`powershell
$login = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/auth/login" \`
  -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}'
$headers = @{ Authorization = "Bearer $($login.token)" }

$sid = (Invoke-RestMethod -Method Post -Uri "http://localhost:8000/sessions" -Headers $headers).id
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/sessions/$sid/data" \`
  -Headers $headers -Form @{ file = Get-Item "examples/ambiguous.csv" }

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/sessions/$sid/problem" \`
  -Headers $headers -ContentType "application/json" \`
  -Body '{"text":"Which group should we focus on?"}'

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/sessions/$sid/confirm" \`
  -Headers $headers -ContentType "application/json" -Body '{"edits":{}}'

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/sessions/$sid/options" \`
  -Headers $headers -ContentType "application/json" -Body '{"use_ai":false}'

Invoke-RestMethod -Method Get -Uri "http://localhost:8000/sessions/$sid/decision" -Headers $headers

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/sessions/$sid/deck" -Headers $headers
Invoke-WebRequest -Uri "http://localhost:8000/sessions/$sid/deck.pptx" -Headers $headers -OutFile "test.pptx"
\`\`\`

Check: \`POST /deck\` returns \`deck_ready\`, then \`GET /deck.pptx\` returns a valid PPTX.

---

## 9. What “good” looks like

- The agent asks only about missing required fields, never repeats a question.
- The deck has up to 18 slides, one message per slide.
- Sources are deduplicated and numbered; every \`[n]\` resolves.
- The recommendation names the runner-up and why not the others.
- Confidence reflects the sensitivity scenarios and evidence strength.
- The deck says “No external research used” when research is off or unavailable.
- Reloading the page keeps your step and session.
`,
  },
};
