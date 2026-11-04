import { notFound } from "next/navigation";
import { getDocsNeighbors, getDocsPage } from "@/lib/docs";
import { DocsContent } from "@/components/docs/docs-content";
import { DocsPagination } from "@/components/docs/docs-pagination";
import { DocsToc } from "@/components/docs/docs-toc";

export default async function DocsPage({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}) {
  const { slug } = await params;
  const page = getDocsPage(slug.join("/"));
  if (!page) notFound();
  const { prev, next } = getDocsNeighbors(slug.join("/"));

  return (
    <div className="flex gap-10">
      <div className="min-w-0 flex-1">
        <DocsContent markdown={page.content} />
        <DocsPagination prev={prev} next={next} />
      </div>
      <aside className="hidden w-56 shrink-0 xl:block">
        <DocsToc markdown={page.content} />
      </aside>
    </div>
  );
}
