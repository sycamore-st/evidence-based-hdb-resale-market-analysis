import Link from "next/link"

import { ArticlePager } from "@/components/content/article-shell"
import { MarkdownArticleBody } from "@/components/content/markdown-article-body"
import type { ArticleDocument, ArticleMeta, ArticleSection } from "@/lib/content"

export function ArticleVariantC({
  article,
  section,
  previous,
  next,
}: {
  article: ArticleDocument
  section: ArticleSection
  previous: ArticleMeta | null
  next: ArticleMeta | null
}) {
  return (
    <main className="article-page article-page-c">
      <section className="article-scene-c">
        <aside className="article-panel-c">
          <div className="article-panel-c-brand">HDB Resale Web</div>

          <div className="article-panel-c-copy">
            <p>{article.meta.kicker}</p>
            <h1>{article.meta.title}</h1>
            <span>{article.meta.description}</span>
          </div>

          <div className="article-panel-c-actions">
            <Link href={`/${section}`}>Open section</Link>
            <Link href="/">Back to index</Link>
          </div>

          <div className="article-panel-c-meta">
            <small>{article.meta.readingLabel}</small>
            <strong>{section === "section2" ? "Markdown case note" : "Markdown policy note"}</strong>
          </div>
        </aside>

        <div className="article-content-c">
          <div className="article-content-c-topnav">
            <nav>
              <Link href="/section1/dashboard-1">Dashboards</Link>
              <Link href="/section2">Section 2</Link>
              <Link href="/section3">Section 3</Link>
            </nav>
            <Link href="/" className="article-content-c-home">
              Back to index
            </Link>
          </div>

          <div className="article-c-overview">
            <div className="article-c-overview-copy">
              <p>{article.meta.description}</p>
              <p>
                This version treats the markdown as a designed editorial case page: a fixed narrative panel on the
                left, and a lighter analysis surface on the right for outputs, figures, and the long-form writeup.
              </p>
            </div>
          </div>

          <article className="article-card article-card-c">
            <MarkdownArticleBody body={article.body} />
            <ArticlePager section={section} previous={previous} next={next} />
          </article>
        </div>
      </section>
    </main>
  )
}
