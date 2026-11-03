# Briefing Deck Agent

Sign in, enter a decision or topic, upload raw data (CSV, Excel, JSON) or scrape a web table, edit the slide plan, and download a short PowerPoint.

Full documentation: [DOCS.md](DOCS.md)

## Run
```
pip install -r requirements.txt
copy .env.example .env      # then edit .env with your keys (Windows)
cp .env.example .env        # macOS/Linux
streamlit run app.py
```
Demo login: `admin` / `admin123`. **Change it before real use:**
```
python manage_users.py add yourname
python manage_users.py remove admin
```
There is no sign-up in the app. Accounts are issued with `manage_users.py`.

### Simple user access (recommended)
Edit `access.json` to add users — no script needed:

```json
{
  "users": {
    "admin": { "password": "admin123", "role": "admin" },
    "viewer": { "password": "view123", "role": "viewer" }
  }
}
```

`admin` gets full access (AI + offline kit); `viewer` can load data, plan and download the deck but not use AI or the offline kit. Changes apply immediately. `access.json` is git-ignored; use `access.example.json` as the template.

After signing in, a signed cookie keeps you logged in for 7 days, so refreshing the page no longer asks for your password again. Set `SESSION_DAYS` in `.env` to change this. The signing key is generated once into `.auth_secret` (git-ignored) unless you set `APP_SECRET`.

## Offline template
The sidebar button "Download offline kit (.zip)" gives a zip with `cli.py`, `core/` and `config.json` (no UI, no sign-in):
```
python cli.py data.csv --topic "Expand bus fleet" --org "My Team" --out briefing.pptx
```
Edit `config.json` to change which slides are on, the colour, and chart or table limits.

## Options
- `--template base.pptx`: build on your own branded PowerPoint (save it as .pptx).
- `--ai`: AI-drafted context and actions. Needs a Groq key. It does not browse the web, so verify everything it writes.

## AI provider (Groq or LongCat)
Keys and secrets live in `.env`, which is loaded automatically at startup and ignored by git. The optional AI step works with either provider (both use an OpenAI-compatible API).

1. Copy the template: `copy .env.example .env` (Windows) or `cp .env.example .env`.
2. Choose a provider with `AI_PROVIDER=groq` or `AI_PROVIDER=longcat` (required — there is no built-in default).
3. Set the matching key in `.env`:
   - **Groq** — get a key at https://console.groq.com/keys → `GROQ_API_KEY=...`
   - **LongCat** — get a key at https://longcat.chat/platform/docs → `LONGCAT_API_KEY=...`
4. Set the model for each provider in `.env`: `GROQ_MODEL=...` and `LONGCAT_MODEL=...`. Optional `AI_MAX_TOKENS` (default `2000`) controls the response length for slide content.

Real environment variables take precedence over `.env`. The offline kit includes `.env.example` but never your `.env`.

## Layout
```
app.py         Streamlit UI (sign-in, data, plan editor, download)
cli.py         offline command line
manage_users.py  add/remove/list users
config.json    slides, colours, limits
DOCS.md        full project documentation
.env           your keys (git-ignored, never shared)
.env.example   template for .env
access.json    simple users/roles (plain passwords, git-ignored)
access.example.json  template for access.json
.auth_secret   auto-generated login-cookie signing key (git-ignored)
core/          data, analyze, plan, build, scraper, research, auth
```

## Notes
- The active tab is stored in the URL (`?tab=...`), so refreshing keeps you on the same tab.
- The Download tab also offers **Download build script (.py)** — a standalone script that rebuilds `briefing.pptx` from the current plan and data. Run it from the project root: `python build_briefing.py`.
- If a selector matches nothing, the scraper extracts the page's headings, paragraphs and list items instead, so you still see the content. Use `table tr` for real tables.
- The scraper only fetches pages your machine can reach. Respect each site's terms and robots.txt.
- `access.json` holds simple plain-password users/roles; `users.json` holds PBKDF2 hashes from `manage_users.py`. For production use, put the app behind HTTPS and consider SSO.
