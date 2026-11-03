# Briefing Deck Agent — Project Documentation

A local tool that turns raw data into a short, editable PowerPoint briefing. You can load a CSV/Excel/JSON file or scrape a web page, draft a slide plan (optionally with AI context and actions), edit it, and download a `.pptx`.

---

## 1. Features

- **Sign-in gate** with PBKDF2-hashed users and a persistent 7-day session cookie.
- **Data input**
  - Upload CSV, XLSX, or JSON.
  - Scrape a web page by CSS selector (tables, headings, lists, paragraphs).
  - Automatic page-text fallback when the selector matches nothing.
- **Analysis**
  - Detects a numeric metric and a grouping category.
  - Computes totals, top/lowest groups, shares, and row counts.
- **Slide planning**
  - Editable titles and bullets.
  - Toggle slides on/off and reorder them.
  - Optional branded `.pptx` template.
  - Optional AI-drafted context and actions (Groq or LongCat).
- **Downloads**
  - `briefing.pptx`
  - Standalone `build_briefing.py` that rebuilds the deck
  - Loaded data as CSV
  - Offline kit (`.zip`) for command-line use
- **Offline CLI** for running without the UI or sign-in.
- **Tab persistence** — refreshing keeps you on the same tab.

---

## 2. Project structure

```
ppt agent/
├── app.py                 Streamlit UI (sign-in, data, plan, download)
├── cli.py                 Offline command-line mode
├── manage_users.py        Add / remove / list users
├── config.json            Slide settings, theme colour, chart/table limits
├── requirements.txt       Python dependencies
├── sample_data.csv        Example data
├── README.md              Quick start
├── DOCS.md                This document
├── .env                   Your keys and AI settings (git-ignored)
├── .env.example           Template for .env
├── access.json            Simple users/roles (plain passwords, git-ignored)
├── access.example.json    Template for access.json
├── .auth_secret           Auto-generated login-cookie signing key (git-ignored)
├── .gitignore             Ignores secrets, venv, cache, generated .pptx
├── users.json             PBKDF2 password hashes (legacy)
└── core/
    ├── __init__.py        Loads .env at startup
    ├── auth.py            Users, password hashing, session tokens
    ├── data.py            CSV / Excel / JSON loading
    ├── scraper.py         Web page scraping
    ├── analyze.py         Metric / category analysis
    ├── plan.py            Slide plan generation
    ├── build.py           PowerPoint builder
    └── research.py        Optional AI step (Groq / LongCat)
```

---

## 3. Requirements

- Python 3.10+
- Streamlit **1.65+** (uses `st.pills`, `st.iframe`, `st.query_params`, `st.context.cookies`)
- Packages listed in `requirements.txt`

```powershell
pip install -r requirements.txt
```

---

## 4. Quick start (web UI)

```powershell
# 1. Create your local settings
copy .env.example .env
# 2. Edit .env and add your AI key(s)
# 3. Run the app
.\venv\Scripts\streamlit.exe run app.py
```

Open the printed local URL (default `http://localhost:8501`).

Demo login: `admin` / `admin123` — **change it before real use**:

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
- `.env` is git-ignored and is never included in the offline kit.

### 5.2 `config.json`

```json
{
  "organisation": "Your Organisation",
  "theme": { "primary": "01411C" },
  "slides": { "summary": true, "key_figures": true, "chart": true, "table": false, "actions": true },
  "max_chart_items": 6,
  "table_rows": 8,
  "table_cols": 6
}
```

| Key | Meaning |
|---|---|
| `organisation` | Default organisation shown on the title slide |
| `theme.primary` | Hex colour for slide titles and charts (no `#`) |
| `slides.summary` | Include the Summary slide |
| `slides.key_figures` | Include the Key figures slide |
| `slides.chart` | Include the chart slide |
| `slides.table` | Include the data table slide |
| `slides.actions` | Include the Recommended actions slide |
| `max_chart_items` | Maximum categories shown in the chart |
| `table_rows` / `table_cols` | Data table size limits |

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

- `role: admin` — full access, including the AI step and the offline-kit download.
- `role: viewer` — can load data, draft/edit the plan and download the deck, but cannot use the AI step or download the offline kit.
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

## 8. Slide planning

1. **Load data** in tab 1.
2. In tab 2, enter a **Decision or topic** and **Organisation** (placeholders show examples; blanks fall back to `Briefing` and the configured organisation).
3. Optionally upload a branded `.pptx` template.
4. Optionally enable **Add AI-drafted context and actions**.
5. Click **Draft slide plan**.

The plan contains:

1. Title slide
2. Summary
3. Key figures
4. Chart
5. Data table (off by default)
6. Recommended actions

You can edit titles and bullets, toggle slides, and reorder them with Up/Down.

### AI step

- The AI step does **not** browse the web. Treat its output as a draft and verify it.
- It uses the OpenAI-compatible API for either provider.
- The model and provider come from `.env`; nothing is hardcoded in the app.
- `AI_MAX_TOKENS` controls the response length (default 2000).
- The AI checkbox is disabled when the provider, key, or model is missing.

---

## 9. Downloads

| Where | Button | File |
|---|---|---|
| Sidebar | Download offline kit (.zip) | `briefing_kit.zip` |
| Tab 1 | Download loaded data (.csv) | `loaded_data.csv` |
| Tab 3 | Download briefing.pptx | `briefing.pptx` |
| Tab 3 | Download build script (.py) | `build_briefing.py` |

### `build_briefing.py`

A standalone script generated from the current plan, data, analysis and config. Run it from the project root:

```powershell
python build_briefing.py
```

It writes `briefing.pptx` next to the script.

### Offline kit

The zip contains `cli.py`, `config.json`, `requirements.txt`, `sample_data.csv`, `README.md`, `.env.example` and `core/` (except `auth.py`). It does not contain `.env`, `.auth_secret`, or user data.

---

## 10. Offline CLI

```powershell
python cli.py data.csv --topic "Expand bus fleet" --org "My Team" --out briefing.pptx
```

Options:

| Option | Meaning |
|---|---|
| `data` | Path to CSV / Excel / JSON |
| `--topic` | Decision or topic (default `Briefing`) |
| `--org` | Organisation (defaults to `config.json`) |
| `--config` | Alternate config path |
| `--template` | Branded `.pptx` template |
| `--ai` | Add AI-drafted context and actions |
| `--out` | Output path (default `briefing.pptx`) |

The CLI has no sign-in and no UI. It uses the same `.env` settings for the AI step.

---

## 11. Tab persistence

The active tab is stored in the URL as `?tab=...`. Refreshing the page keeps you on the same tab. Only the selected tab is rendered.

---

## 12. Core module reference

| Module | Responsibility |
|---|---|
| `core/__init__.py` | Loads `.env` before anything reads environment variables |
| `core/auth.py` | User hashes, token signing/verification, session TTL |
| `core/data.py` | CSV / Excel / JSON loading with delimiter sniffing |
| `core/scraper.py` | HTTP fetch, CSS selection, table/text extraction |
| `core/analyze.py` | Metric/category detection and summary statistics |
| `core/plan.py` | Slide plan structure and default actions |
| `core/build.py` | PowerPoint generation, charts, tables, templates |
| `core/research.py` | AI provider selection, model config, JSON response parsing |

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
- The response must be JSON with `background` and `actions` arrays; anything else raises an error.

---

## 13. Security notes

- `.env`, `.auth_secret`, `users.json` and generated `.pptx` files should not be shared or committed.
- Passwords are PBKDF2 hashes, not plaintext.
- Session cookies are HMAC-signed and expiring.
- For production, put the app behind HTTPS and consider SSO.
- The scraper only fetches pages your machine can reach; respect each site's terms and `robots.txt`.

---

## 14. Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| Login screen keeps appearing after refresh | Cookie not set / `.auth_secret` changed | Restart Streamlit, sign in again |
| AI checkbox disabled | Missing provider, key, or model | Check `.env`: `AI_PROVIDER`, `GROQ_API_KEY`/`LONGCAT_API_KEY`, `GROQ_MODEL`/`LONGCAT_MODEL` |
| `ModuleNotFoundError: openai` | Dependencies not installed | `pip install -r requirements.txt` |
| Scrape says "no table" | Page has no `<table>` | Use `h2`, `li`, or accept the page-text fallback |
| Scrape returns almost nothing | Page is JavaScript-rendered | Use the site's export/API or copy the data |
| CSV tokenizing error | Wrong delimiter or ragged rows | The loader sniffs delimiters and skips bad rows; check the file |
| Refresh returns to Data tab | Old app version | Restart Streamlit; tab is stored in `?tab=` |
| Port already in use | Another Streamlit process | Stop it or use `--server.port 8502` |

---

## 15. Development

- Run the app with `streamlit run app.py`.
- The offline kit is generated in memory by `offline_kit()` in `app.py`.
- The build script is generated by `build_script()` in `app.py`.
- `manage_users.py` supports `add`, `remove`, and `list`.
- Tests are manual/browser-based; there is no automated test suite.

---

## 16. Changelog (recent)

- Added Groq and LongCat AI providers via `.env`.
- Added persistent login cookies and tab persistence.
- Added downloadable `build_briefing.py`.
- Added page-text fallback and scrape presets.
- Added CSV delimiter sniffing and ragged-row handling.
- Added placeholder hints for topic and organisation.
- Replaced deprecated `use_container_width` with `width="stretch"`.
