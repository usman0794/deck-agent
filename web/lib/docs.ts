import { docsContent } from "./docs-content";

export interface DocsNavItem {
  label: string;
  slug: string;
}

export interface DocsNavSection {
  label: string;
  items: DocsNavItem[];
}

export const docsNav: DocsNavSection[] = [
  {
    label: "Overview",
    items: [
      { label: "What is Briefing Deck Agent?", slug: "overview" },
      { label: "Getting Started", slug: "getting-started" },
      { label: "Configuration", slug: "configuration" },
    ],
  },
  {
    label: "Using the App",
    items: [
      { label: "Data Input", slug: "data-input" },
      { label: "Problem & Understanding", slug: "problem" },
      { label: "Deep Research", slug: "research" },
      { label: "Options & Decision", slug: "decision" },
      { label: "Deck & Downloads", slug: "deck" },
    ],
  },
  {
    label: "API",
    items: [
      { label: "API Overview", slug: "api-overview" },
      { label: "Authentication", slug: "api-auth" },
      { label: "Sessions", slug: "api-sessions" },
      { label: "Research", slug: "api-research" },
    ],
  },
  {
    label: "Reference",
    items: [
      { label: "AI Providers", slug: "ai-providers" },
      { label: "Security & Privacy", slug: "security" },
      { label: "FAQ & Troubleshooting", slug: "faq" },
      { label: "Developer Guide", slug: "developer-guide" },
      { label: "Test Plan", slug: "test-plan" },
    ],
  },
];

export function getDocsPage(slug: string) {
  return docsContent[slug];
}

export function getDocsNeighbors(slug: string) {
  const flat = docsNav.flatMap((section) => section.items);
  const index = flat.findIndex((item) => item.slug === slug);
  return {
    prev: index > 0 ? flat[index - 1] : undefined,
    next: index >= 0 && index < flat.length - 1 ? flat[index + 1] : undefined,
  };
}

export function slugify(text: string) {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

export function extractHeadings(markdown: string) {
  const headings: { level: number; text: string; id: string }[] = [];
  let inCode = false;
  for (const line of markdown.split("\n")) {
    if (line.trim().startsWith("```")) inCode = !inCode;
    if (inCode) continue;
    const match = line.match(/^(#{2,3})\s+(.*)$/);
    if (match) {
      const text = match[2].trim();
      headings.push({ level: match[1].length, text, id: slugify(text) });
    }
  }
  return headings;
}
