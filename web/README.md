# Briefing Deck Agent — Web UI

Next.js + Tailwind CSS + shadcn/ui frontend for the Briefing Deck Agent API.

## Run

```bash
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:3000 and sign in.

## Flow

1. **Login** — existing user accounts.
2. **Data** — upload CSV/Excel/JSON or scrape a web table.
3. **Problem** — describe the situation in plain words; confirm what the agent understood.
4. **Research** — optional external research (good practices, benchmarks, risks).
5. **Options** — three evidence-backed solutions; adjust ratings if needed.
6. **Decision** — confidence, recommendation, why-not-the-others, download the deck.

## shadcn/ui

Components live in `components/ui/`. Add more with:

```bash
npx shadcn@latest add <component>
```

The API contract is documented in `../docs/api_contract.md`.
