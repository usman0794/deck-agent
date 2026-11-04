"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function DocsContent({ markdown }: { markdown: string }) {
  return (
    <div className="prose prose-neutral max-w-none dark:prose-invert">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
    </div>
  );
}
