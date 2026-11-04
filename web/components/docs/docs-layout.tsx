"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { docsNav } from "@/lib/docs";
import { DocsSearch } from "./docs-search";

export function DocsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [dark, setDark] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("docs-theme");
    if (stored === "dark") {
      setDark(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("docs-theme", next ? "dark" : "light");
  }

  const nav = (
    <nav className="space-y-6">
      {docsNav.map((section) => (
        <div key={section.label}>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {section.label}
          </p>
          <ul className="space-y-1">
            {section.items.map((item) => {
              const active = pathname === `/docs/${item.slug}`;
              return (
                <li key={item.slug}>
                  <Link
                    href={`/docs/${item.slug}`}
                    onClick={() => setMenuOpen(false)}
                    className={`block rounded-md px-3 py-2 text-sm transition-colors ${
                      active
                        ? "bg-accent font-medium text-primary"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4">
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-primary text-xs text-primary-foreground">
              B
            </span>
            Briefing Deck Agent
          </Link>
          <span className="text-sm text-muted-foreground">Docs</span>
          <div className="ml-auto flex items-center gap-2">
            <DocsSearch />
            <button
              onClick={toggleTheme}
              className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent"
            >
              {dark ? "Light" : "Dark"}
            </button>
            <Link
              href="/dashboard"
              className="hidden rounded-md border px-3 py-1.5 text-sm hover:bg-accent sm:inline"
            >
              Open app
            </Link>
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent lg:hidden"
            >
              {menuOpen ? "Close" : "Menu"}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl gap-8 px-4 py-8">
        <aside className="hidden w-64 shrink-0 lg:block">
          <div className="sticky top-20">{nav}</div>
        </aside>
        {menuOpen && (
          <div className="fixed inset-0 top-14 z-30 overflow-y-auto bg-background p-4 lg:hidden">
            {nav}
          </div>
        )}
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
