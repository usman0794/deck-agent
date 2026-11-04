# Briefing Deck Agent — Web UI

Next.js + Tailwind CSS + shadcn/ui frontend for the Briefing Deck Agent API.

## Run

```bash
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:3000 and sign in.

## Documentation

The app ships with a Kept-style documentation site at **http://localhost:3000/docs**:

- Sidebar navigation with sections
- Client-side search
- Light / dark theme toggle
- "On this page" table of contents
- Prev / next pagination
- Responsive layout with a mobile menu

The docs content lives in `lib/docs-content.ts`; the navigation lives in `lib/docs.ts`.

## App flow

1. **Login** — existing user accounts.
2. **Data** — upload CSV/Excel/JSON or scrape a web table.
3. **Problem** — describe the situation in plain words; confirm what the agent understood.
4. **Research** — optional external research (good practices, benchmarks, risks).
5. **Options** — three evidence-backed solutions; adjust ratings if needed.
6. **Decision** — confidence, recommendation, why-not-the-others, download the deck.

The session is stored in \`localStorage\`, so refreshing the page keeps your step, data status, intent, research, options and decision.

## shadcn/ui

Components live in `components/ui/`. Add more with:

```bash
npx shadcn@latest add <component>
```

The API contract is documented in `../docs/api_contract.md`.

