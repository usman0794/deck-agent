import Link from "next/link";

export function DocsPagination({
  prev,
  next,
}: {
  prev?: { slug: string; label: string };
  next?: { slug: string; label: string };
}) {
  return (
    <div className="mt-12 flex items-center justify-between gap-4 border-t pt-6">
      {prev ? (
        <Link
          href={`/docs/${prev.slug}`}
          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          ← {prev.label}
        </Link>
      ) : (
        <span />
      )}
      {next ? (
        <Link
          href={`/docs/${next.slug}`}
          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          {next.label} →
        </Link>
      ) : (
        <span />
      )}
    </div>
  );
}
