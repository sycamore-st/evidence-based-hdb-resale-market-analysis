import Link from "next/link"

import type { ArticleMeta, ArticleSection } from "@/lib/content"

function formatSectionLabel(section: ArticleSection): string {
  return section === "section2" ? "Section 2" : "Section 3"
}

export function ArticleTopNav({ section }: { section: ArticleSection }) {
  return (
    <div className="article-topnav">
      <Link href="/">Back to index</Link>
      <Link href="/section1/dashboard-1">Section 1</Link>
      <Link href="/section2">Section 2</Link>
      <Link href="/section3">Section 3</Link>
      <span>{formatSectionLabel(section)}</span>
    </div>
  )
}

export function ArticlePager({
  section,
  previous,
  next,
}: {
  section: ArticleSection
  previous: ArticleMeta | null
  next: ArticleMeta | null
}) {
  return (
    <div className="article-pager">
      {previous ? (
        <Link href={`/${section}/${previous.slug}`} className="article-pager-link">
          <small>Previous</small>
          <strong>{previous.title}</strong>
        </Link>
      ) : (
        <div />
      )}
      {next ? (
        <Link href={`/${section}/${next.slug}`} className="article-pager-link article-pager-link-next">
          <small>Next</small>
          <strong>{next.title}</strong>
        </Link>
      ) : null}
    </div>
  )
}
