import { ArticlePager } from "@/components/content/article-shell"
import { SectionDashboardNav } from "@/components/section1/dashboard-shared"
import { ValuationWorkbench } from "@/components/section2/valuation-workbench"
import type { ArticleDocument, ArticleMeta } from "@/lib/content"

export function QuestionBExtendedInlinePage({
  article,
  previous,
  next,
}: {
  article: ArticleDocument
  previous: ArticleMeta | null
  next: ArticleMeta | null
}) {
  return (
    <main className="article-page valuation-inline-page dashboard2-page">
      <section className="section-landing-shell valuation-inline-shell">
        <header className="dashboard2-header valuation-inline-header">
          <div>
            <p className="dashboard2-kicker">{article.meta.kicker}</p>
            <h1>{article.meta.title}</h1>
            <p>{article.meta.description}</p>
            <p className="open-source-note">
              Open source on{" "}
              <a
                href="https://github.com/sycamore-st/evidence-based-hdb-resale-market-analysis"
                target="_blank"
                rel="noreferrer"
              >
                GitHub
              </a>
              .
            </p>
          </div>
          <div className="dashboard2-header-actions">
            <SectionDashboardNav className="dashboard2-header-actions-links" />
          </div>
        </header>
        <section className="valuation-inline-tool">
          <ValuationWorkbench />
        </section>

        <ArticlePager section="section2" previous={previous} next={next} />
      </section>
    </main>
  )
}
