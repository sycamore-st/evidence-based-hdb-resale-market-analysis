import Link from "next/link"

import { ArticleTopNav } from "@/components/content/article-shell"
import type { ArticleMeta, ArticleSection } from "@/lib/content"

export function SectionLanding({
  section,
  title,
  description,
  articles,
}: {
  section: ArticleSection
  title: string
  description: string
  articles: ArticleMeta[]
}) {
  return (
    <main className="section-landing-page">
      <section className="section-landing-shell">
        <ArticleTopNav section={section} />

        <header className="section-landing-hero">
          <p>{section === "section2" ? "Section 2 / Case writeups" : "Section 3 / Case writeups"}</p>
          <h1>{title}</h1>
          <span>{description}</span>
        </header>

        <div className="section-landing-grid">
          {articles.map((article) => (
            <Link key={article.slug} href={`/${section}/${article.slug}`} className="section-landing-card">
              <p>{article.kicker}</p>
              <h2>{article.title}</h2>
              <span>{article.description}</span>
              <strong>Read article</strong>
            </Link>
          ))}
        </div>
      </section>
    </main>
  )
}
