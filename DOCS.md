# Briefing Deck Agent — Project Documentation

A local tool that turns raw data into an evidence-backed decision deck. Upload a CSV/Excel/JSON file or scrape a web page, describe the problem in plain words, optionally research it externally, and get three solutions, a recommendation, and a detailed `.pptx`.

---

## 1. Features

- **Sign-in gate** with PBKDF2-hashed users and a persistent 7-day session cookie.
- **Data input**
  - Upload CSV, XLSX, or JSON.
  - Scrape a web page by CSS selector (tables, headings, lists, paragraphs).
  - Automatic page-text fallback when the selector matches nothing.
- **Understanding**
  - Classifies the problem type (improve, prioritise, allocate, diagnose, choose).
  - Extracts the goal, metric, group, constraints and audience from plain words.
  - Asks clarifying questions only when required, never repeats them.
- **Deep research (optional)**
  - Plans sub-questions, searches, fetches safely, verifies snippets, and groups findings into themes.
  - Rule-based fallback when no search provider or key is available.
- **Decision**
  - Three evidence-backed options with code-computed estimates.
  - Weighted scoring, 6-scenario sensitivity, confidence with reasons.
  - "Why not the others" and human-decision tie handling.
- **Deck** — up to 18 slides with speaker notes, sources, roadmap, risks and KPIs.
- **Interfaces** — Next.js + Tailwind CSS + shadcn/ui frontend (`web/`), FastAPI backend (`api/`), offline CLI (`cli.py`).

---

## 2. Project structure

```
ppt agent/
├── web/                   Next.js + Tailwind CSS + shadcn/ui frontend
│   ├── app/               Pages (login, dashboard)
│   ├── components/ui/     shadcn/ui components
│   └── lib/               API client and types
├── api/                   FastAPI backend
├── service/               UI-independent session workflow
├── core/                  Pure logic (data, understand, decide, check, plan, build, research, auth)
├── cli.py                 Offline command-line mode
├── manage_users.py        Add / remove / list users
├── config.json            Slides, colours, limits, research settings
├── requirements.txt       Python dependencies
├── sample_data.csv        Example data
├── README.md              Quick start
├── DOCS.md                This document
├── docs/                  API contract
├── .env                   Your keys and AI settings (git-ignored)
├── .env.example           Template for .env
├── access.json            Simple users/roles (plain passwords, git-ignored)
├── access.example.json    Template for access.json
├── .auth_secret           Auto-generated login-cookie signing key (git-ignored)
├── .gitignore             Ignores secrets, venv, cache, generated .pptx
└── users.json             PBKDF2 password hashes
```

---

## 3. Requirements

- Python 3.10+
- Node.js 20+ (for the Next.js frontend)
- Packages listed in `requirements.txt` (backend) and `web/package.json` (frontend)

```powershell
pip install -r requirements.txt
cd web
npm install
```

---

## 4. Quick start

```powershell
# Backend
pip install -r requirements.txt
copy .env.example .env      # then edit .env with your keys
uvicorn api.main:app --reload

# Frontend (new terminal)
cd web
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:3000. Demo login: `admin` / `admin123` — **change it before real use**:

```powershell
python manage_users.py add yourname
python manage_users.py remove admin
```

---

## 5. Configuration

### 5.1 `.env`

Loaded automatically at startup by `core/__init__.py`. Real environment variables take precedence over `.env`.

```ini
GROQ_API_KEY=
LONGCAT_API_KEY=

# groq or longcat (required — there is no built-in default)
AI_PROVIDER=groq

# Model for each provider (required for the AI step)
GROQ_MODEL=openai/gpt-oss-120b
LONGCAT_MODEL=LongCat-2.0
```

Optional settings:

```ini
# Max tokens for the AI response (default 2000)
AI_MAX_TOKENS=2000

# How many days the login cookie stays valid (default 7)
SESSION_DAYS=7

# Optional: override the login-cookie signing key
# APP_SECRET=replace-with-a-long-random-string
```

Notes:

- `AI_PROVIDER` must be `groq` or `longcat`. If it is missing, the AI checkbox is disabled and the AI step reports what to set.
- `GROQ_MODEL` / `LONGCAT_MODEL` select the model for each provider.
- `.env` is git-ignored and never committed.

### 5.2 `config.json`

```json
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
```

| Key | Meaning |
|---|---|
| `organisation` | Default organisation shown on the title slide |
| `theme.primary` | Hex colour for slide titles and charts (no `#`) |
| `slides.*` | Toggle each slide; `max_slides` caps the deck at 18 |
| `max_chart_items` | Maximum categories shown in the chart |
| `table_rows` / `table_cols` | Data table size limits |
| `search.provider` | `ddgs` (no key) or `key` (key-based provider) |
| `search.env_var` | Env var that holds the search key when `provider` is `key` |
| `research.max_seconds` | Total research time budget (default 120 s) |
| `research.max_model_calls` | AI call cap for research (default 25) |
| `research.max_queries` / `max_pages` | Search query / page fetch caps |
| `research.cache_dir` | Folder for the fetched-page cache (`cache/`) |

---

## 6. Authentication and sessions

### Simple user file: `access.json` (recommended)

Edit `access.json` to add users. Passwords are plain text; the role is optional.

```json
{
  "users": {
    "admin": { "password": "admin123", "role": "admin" },
    "viewer": { "password": "view123", "role": "viewer" }
  }
}
```

- `role: admin` — full access, including the AI step and research.
- `role: viewer` — can load data, draft/edit the plan and download the deck, but cannot use the AI step or research.
- Changes take effect immediately; the file is read on every sign-in and session restore.
- `access.json` is git-ignored because it contains plain passwords. Use `access.example.json` as the template.

### Hashed users: `users.json`

`manage_users.py` writes PBKDF2-SHA256 hashes (200,000 iterations) to `users.json`. The app checks `access.json` first, then `users.json`, so both can coexist.

### Sessions

- After sign-in, the app sets a signed `bdauth` cookie that keeps you logged in for `SESSION_DAYS` (default 7).
- The cookie is an HMAC-signed token containing the username and expiry. It is rejected if:
  - the signature does not match,
  - it is expired,
  - the user no longer exists in either user file.
- The signing key is read from `APP_SECRET` if set, otherwise generated once into `.auth_secret` (git-ignored).
- Five failed sign-in attempts lock the form until the app is restarted.
- **Sign out** clears the session and the cookie.

---

## 7. Data input

### 7.1 Upload a file

Supported types: `.csv`, `.xlsx`, `.xls`, `.json`.

- CSV parsing sniffs the delimiter (`,`, `;`, tab, `|`) and tolerates ragged rows by skipping the malformed ones.
- The preview shows all rows and can be downloaded again as `loaded_data.csv`.

### 7.2 Scrape a web page

Enter a URL and choose what to extract:

| Preset | Selector | Use for |
|---|---|---|
| Table rows | `table tr` | Real HTML tables |
| Section headings | `h2` | Page sections |
| Lists and cards | `li` | List items |
| Paragraphs | `p` | Paragraph text |
| Custom selector… | your own CSS | Anything else |

Behaviour:

- URLs without a scheme get `https://` added.
- If the selector matches nothing, the scraper extracts the page's headings, paragraphs and list items into an `element` / `text` table, and shows a warning.
- Navigation, script, style and form content is skipped in the fallback.
- Duplicate text blocks are removed.
- If the downloaded HTML is almost empty, the page is likely JavaScript-rendered and the scraper explains that it cannot run JavaScript.

Good test pages:

| Site | URL | Selector |
|---|---|---|
| W3Schools tables | `https://www.w3schools.com/html/html_tables.asp` | `table tr` |
| Scrape This Site — hockey | `https://www.scrapethissite.com/pages/forms/` | `table.table tr` |
| Wikipedia — countries by population | `https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)` | `table.wikitable tr` |
| Scrape This Site — countries | `https://www.scrapethissite.com/pages/simple/` | `.country` |
| Quotes to Scrape | `https://quotes.toscrape.com/` | `.quote` |
| Books to Scrape | `https://books.toscrape.com/` | `article.product_pod` |

---

## 8. Decision flow

1. **Load data** — upload a file or scrape a web table.
2. **Describe the problem** in plain words. The agent extracts the goal, metric, group, constraints and audience, and shows what it understood.
3. **Confirm** the understanding (or answer a few clarifying questions first).
4. **Research (optional)** — search the web for good practices, causes, benchmarks and risks.
5. **Options** — three evidence-backed solutions with ratings; adjust ratings if needed.
6. **Decision** — confidence, recommendation, why-not-the-others, and the downloadable deck.

### Research step

- Searches use only the generic problem wording; group names, row values, file names and PII are stripped from queries.
- Fetched pages are untrusted data: snippets are verified against the page text, and prompt-injection phrases are flagged and ignored.
- Every AI step has a rule-based fallback, so the app works with no key and no network.

---

## 9. Downloads

| Where | Action | File |
|---|---|---|
| Decision step | Download deck | `briefing.pptx` |
| API | `POST /sessions/{id}/deck` then `GET /sessions/{id}/deck.pptx` | `briefing.pptx` |
| CLI | `--out briefing.pptx` | `briefing.pptx` |

The UI and API **build the deck before downloading**; calling `GET` before `POST` returns `404`.

The deck contains up to 18 slides: title, executive summary, problem, data, chart, research findings, good practices, three solutions, comparison, criteria, robustness, recommendation, roadmap, risks, KPIs and sources. Sources are deduplicated by URL and numbered; findings reference those numbers. Speaker notes carry the reasoning on slides 2, 6, 8–10, 13 and 14.

---

## 10. Offline CLI

```powershell
python cli.py data.csv --text "we pay too much overtime and HR needs a plan next month" --out briefing.pptx
```

Options:

| Option | Meaning |
|---|---|
| `data` | Path to CSV / Excel / JSON |
| `--text` | Describe the situation in plain words |
| `--answers` | JSON file or inline JSON with answers to clarifying questions |
| `--topic` / `--goal` / `--metric` / `--category` | Optional overrides |
| `--org` | Organisation (defaults to `config.json`) |
| `--use-ai` | Use AI for option wording (requires a key) |
| `--research` / `--no-research` | Run external research (default on when a search provider is available) |
| `--out` | Output path (default `briefing.pptx`) |

The CLI calls the service layer, so it exercises the same workflow as the API.

---

## 11. Frontend flow

The Next.js UI (`web/`) walks through five steps: **Data → Problem → Research → Options → Decision**. Each step calls the API; the decision step builds the deck before downloading. Loading banners and button states show progress, and research shows page errors when pages are skipped.

---

## 12. Core module reference

| Module | Responsibility |
|---|---|
| `core/__init__.py` | Loads `.env` before anything reads environment variables |
| `core/auth.py` | User hashes, token signing/verification, session TTL |
| `core/data.py` | CSV / Excel / JSON loading with delimiter sniffing |
| `core/scraper.py` | HTTP fetch, CSS selection, table/text extraction |
| `core/analyze.py` | Metric/category detection and summary statistics |
| `core/guardrails.py` | Input, option, decision, output and audit checks |
| `core/problem.py` | Problem-type classification |
| `core/understand.py` | Data profiling and intent extraction |
| `core/archetypes.py` | Domain-neutral solution archetypes |
| `core/decide.py` | Option generation, scoring and recommendation |
| `core/check.py` | Sensitivity, critique, confidence |
| `core/plan.py` | Deck slide structure |
| `core/build.py` | PowerPoint generation, charts, tables, notes |
| `core/research.py` | AI provider selection, model config, JSON response parsing |
| `core/research_web.py` | Deep research: plan, search, fetch, extract, verify, synthesize |
| `service/session.py` | Session model and stores (memory / file) |
| `service/workflow.py` | Session workflow functions |
| `api/main.py` | FastAPI endpoints |
| `web/` | Next.js + Tailwind CSS + shadcn/ui frontend |

### `core.research` details

```python
PROVIDERS = {
    "groq":   {"key_env": "GROQ_API_KEY",   "base_url": "https://api.groq.com/openai/v1"},
    "longcat":{"key_env": "LONGCAT_API_KEY","base_url": "https://api.longcat.chat/openai/v1"},
}
```

- `AI_PROVIDER` selects the provider.
- `GROQ_MODEL` / `LONGCAT_MODEL` select the model.
- `AI_MAX_TOKENS` sets `max_tokens` (default 2000).
- `research.complete_json()` is a shared helper for AI JSON calls; `ai_options()` requests three scored options.
- AI calls time out after **30 s**; every AI step has a rule-based fallback, so the app works with no key and no network.

### `core.research_web` details

- Search providers: `ddgs` (DuckDuckGo, no key) or `key` (generic key-based provider configured in `config.json`).
- Queries are sanitised: column names, group values, file names and PII-like tokens are removed.
- Fetched pages are untrusted: snippets must appear in the page, claims must share key terms with the snippet, and prompt-injection phrases are flagged.
- Sources are deduplicated by URL and numbered; findings reference those numbers.
- Low-quality claims (maintenance/offline/error/outage text) are dropped.
- `page_errors` lists pages skipped by robots.txt, timeouts or HTTP errors.
- Limits: 25 model calls, 120 s, 6 queries, 10 pages; exceeding them returns `partial`.

---

## 13. Security notes

- `.env`, `.auth_secret`, `access.json`, `users.json`, `cache/`, `sessions/`, `session_data/` and generated `.pptx` files should not be shared or committed.
- Passwords in `access.json` are plain text; `users.json` holds PBKDF2 hashes.
- Session cookies are HMAC-signed and expiring.
- For production, put the API behind HTTPS and consider SSO.
- The scraper only fetches pages your machine can reach, blocks private/local IPs (SSRF), respects `robots.txt`, and honours timeouts and size caps.
- Research queries are sanitised: column names, group values, file names and PII-like tokens are removed before searching.

---

## 14. Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| Login screen keeps appearing | Cookie not set / `.auth_secret` changed | Restart the API and sign in again |
| AI options disabled | Missing provider, key, or model | Check `.env`: `AI_PROVIDER`, `GROQ_API_KEY`/`LONGCAT_API_KEY`, `GROQ_MODEL`/`LONGCAT_MODEL` |
| `ModuleNotFoundError` | Dependencies not installed | `pip install -r requirements.txt` (backend) / `npm install` in `web/` |
| Scrape says "no table" | Page has no `<table>` | Use `h2`, `li`, or accept the page-text fallback |
| Scrape returns almost nothing | Page is JavaScript-rendered | Use the site's export/API or copy the data |
| CSV tokenizing error | Wrong delimiter or ragged rows | The loader sniffs delimiters and skips bad rows; check the file |
| Downloaded `briefing.pptx` won't open | `GET /deck.pptx` called before `POST /deck` | The UI builds first; via API call `POST /sessions/{id}/deck` before downloading |
| Research shows `partial` / skipped pages | robots.txt, timeouts or HTTP 429 | Wait and retry; the deck falls back to data-only options |
| AI step hangs | Provider is slow or unreachable | AI calls time out after 30 s and fall back to rules |
| Port already in use | Another API/frontend process | Stop it or run with `--port 8001` / `-p 3001` |

---

## 15. Development

- Backend: `uvicorn api.main:app --reload`
- Frontend: `cd web && npm run dev`
- CLI: `python cli.py data.csv --text "..."`
- Tests: `pytest`
- `manage_users.py` supports `add`, `remove`, and `list`.
- The API contract lives in `docs/api_contract.md`.
- The frontend and backend are separate apps; the API is the boundary.

---

## 16. Changelog (recent)

- Fixed the deck download: the UI now builds the deck before fetching it, so `briefing.pptx` is always a valid file.
- Deduplicated research sources by URL, numbered them and mapped evidence IDs to those numbers.
- Filtered low-quality research claims (maintenance/offline/error/outage) and capped coverage at 100%.
- Made the deck richer: data totals and top/lowest groups, actual research findings per theme, good practices with source numbers.
- Added research loading states, page-error reporting and 30 s AI timeouts.
- Added `GET /health`.
- Replaced Streamlit with a Next.js + Tailwind CSS + shadcn/ui frontend (`web/`) and a FastAPI backend (`api/`).
- Added problem types, domain-neutral archetypes, guardrails and a service layer.
- Added deep research, evidence-backed options and a detailed 18-slide deck.
- Added persistent login cookies and a pluggable bearer-token API.
- Added CSV delimiter sniffing, page-text fallback and scrape presets.
