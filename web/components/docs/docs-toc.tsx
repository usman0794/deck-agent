"use client";

import { useEffect, useState } from "react";
import { extractHeadings } from "@/lib/docs";

export function DocsToc({ markdown }: { markdown: string }) {
  const [headings, setHeadings] = useState<
    { level: number; text: string; id: string }[]
  >([]);

  useEffect(() => {
    setHeadings(extractHeadings(markdown));
  }, [markdown]);

  if (!headings.length) return null;

  return (
    <nav className="sticky top-20 space-y-1 text-sm">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        On this page
      </p>
      {headings.map((heading) => (
        <a
          key={heading.id}
          href={`#${heading.id}`}
          className={`block text-muted-foreground transition-colors hover:text-foreground ${
            heading.level === 3 ? "pl-4" : ""
          }`}
        >
          {heading.text}
        </a>
      ))}
    </nav>
  );
}
