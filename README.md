# Briefing Deck Agent

Upload raw data, describe a problem in plain words, let the agent research it, and get three evidence-backed solutions, a recommendation, and a detailed PowerPoint deck.

Full documentation: [DOCS.md](DOCS.md) · API contract: [docs/api_contract.md](docs/api_contract.md)

## Architecture

```
web/            Next.js + Tailwind CSS + shadcn/ui frontend
api/            FastAPI backend (sessions, research, decks)
service/        UI-independent session workflow
core/           pure logic (data, understand, decide, check, plan, build, research, auth)
cli.py          offline command line (no UI)
config.json     slides, colours, limits, research settings
docs/           API contract and architecture notes
```

The frontend and backend are **separate applications** with separate dependencies. The API contract is the boundary: the UI never imports Python, and the API never imports React.

## Run

### 1. Backend (FastAPI)

```powershell
pip install -r requirements.txt
copy .env.example .env      # then edit .env with your keys (Windows)
cp .env.example .env        # macOS/Linux
uvicorn api.main:app --reload
```

API docs: http://localhost:8000/docs

### 2. Frontend (Next.js)

```powershell
cd web
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:3000 and sign in.

Demo login: `admin` / `admin123`. **Change it before real use:**

```powershell
python manage_users.py add yourname
python manage_users.py remove admin
```

### 3. CLI (offline, no UI)

```powershell
python cli.py data.csv --text "we pay too much overtime and HR needs a plan next month" --out briefing.pptx
```

## User access

Edit `access.json` to add users — no script needed:

```json
{
  "users": {
    "admin": { "password": "admin123", "role": "admin" },
    "viewer": { "password": "view123", "role": "viewer" }
  }
}
```

`admin` gets full access (AI + research); `viewer` can load data, plan and download the deck but not use AI or research. `access.json` is git-ignored; use `access.example.json` as the template. Hashed users from `manage_users.py` (`users.json`) are also supported.

## AI provider (Groq or LongCat)

Keys and secrets live in `.env`, which is loaded automatically at startup and ignored by git.

1. Copy the template: `copy .env.example .env` (Windows) or `cp .env.example .env`.
2. Choose a provider with `AI_PROVIDER=groq` or `AI_PROVIDER=longcat` (required — there is no built-in default).
3. Set the matching key in `.env`:
   - **Groq** — get a key at https://console.groq.com/keys → `GROQ_API_KEY=...`
   - **LongCat** — get a key at https://longcat.chat/platform/docs → `LONGCAT_API_KEY=...`
4. Set the model for each provider in `.env`: `GROQ_MODEL=...` and `LONGCAT_MODEL=...`.

Real environment variables take precedence over `.env`. Every AI step has a rule-based fallback, so the app works with no key and no network.

## Research (optional)

The agent can search the web for good practices, causes, benchmarks and risks. Configure it in `config.json`:

```json
"search": { "provider": "ddgs", "env_var": "SEARCH_API_KEY", "base_url": "..." },
"research": { "max_seconds": 120, "max_model_calls": 25, "max_queries": 6, "max_pages": 10 }
```

- `ddgs` (DuckDuckGo) needs no key. A key-based provider reads the env var named in config.
- Queries use only the generic problem wording — never group names, row values, file names or PII.
- Sources are deduplicated by URL and numbered; findings reference those numbers.
- Low-quality claims (maintenance/offline/error/outage text) are filtered out.
- Pages skipped by robots.txt, timeouts or HTTP errors are reported in the UI.
- AI calls time out after 30 s; every AI step has a rule-based fallback.

## Notes

- The API is stateless per session; sessions are stored in `sessions/` (file store) or memory (`SESSION_STORE=memory`).
- If a selector matches nothing, the scraper extracts the page's headings, paragraphs and list items instead. Use `table tr` for real tables.
- The scraper only fetches pages your machine can reach. Respect each site's terms and robots.txt.
- The deck is built before download, so `briefing.pptx` is always a valid file.
- For testing, see `docs/test-plan.md` — data schemas, tough questions and expected observations.
- For production use, put the API behind HTTPS and consider SSO.
