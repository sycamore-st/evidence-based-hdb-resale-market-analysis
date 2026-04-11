import Link from "next/link"

import type { ArticleMeta, ArticleSection } from "@/lib/content"
import type { SiteSection } from "@/lib/sections"

export function ArticleTopNav({ section }: { section: SiteSection }) {
  return (
    <div className="article-topnav site-topnav">
      <div className="site-topnav-links">
        {section === "section1" ? (
          <span className="site-topnav-current">Section 1</span>
        ) : (
          <Link href="/section1" className="site-topnav-link">Section 1</Link>
        )}
        {section === "section2" ? (
          <span className="site-topnav-current">Section 2</span>
        ) : (
          <Link href="/section2" className="site-topnav-link">Section 2</Link>
        )}
        {section === "section3" ? (
          <span className="site-topnav-current">Section 3</span>
        ) : (
          <Link href="/section3" className="site-topnav-link">Section 3</Link>
        )}
      </div>
      <Link href="/#menu" className="site-topnav-action">
        Menu
      </Link>
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
