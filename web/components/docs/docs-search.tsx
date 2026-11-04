"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { docsContent } from "@/lib/docs-content";

export function DocsSearch() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return Object.entries(docsContent)
      .filter(
        ([, page]) =>
          page.title.toLowerCase().includes(q) || page.content.toLowerCase().includes(q)
      )
      .slice(0, 8)
      .map(([slug, page]) => ({ slug, title: page.title }));
  }, [query]);

  return (
    <div className="relative">
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Search docs…"
        className="h-9 w-44 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring sm:w-56"
      />
      {open && results.length > 0 && (
        <ul className="absolute right-0 top-10 z-30 w-72 rounded-md border bg-background p-1 shadow-lg">
          {results.map((result) => (
            <li key={result.slug}>
              <button
                onMouseDown={() => {
                  setQuery("");
                  setOpen(false);
                  router.push(`/docs/${result.slug}`);
                }}
                className="block w-full rounded px-2 py-1.5 text-left text-sm hover:bg-accent"
              >
                {result.title}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
