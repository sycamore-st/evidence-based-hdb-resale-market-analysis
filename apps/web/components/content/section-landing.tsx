import Link from "next/link"

import { ArticleTopNav } from "@/components/content/article-shell"
import { getSectionLabel, type SectionLandingItem, type SiteSection } from "@/lib/sections"

export function SectionLanding({
  section,
  title,
  description,
  items,
}: {
  section: SiteSection
  title: string
  description: string
  items: SectionLandingItem[]
}) {
  return (
    <main className="section-landing-page">
      <section className="section-landing-shell">
        {section === "section1" ? (
          <div className="article-topnav site-topnav">
            <div className="site-topnav-links">
              <span className="site-topnav-current">Section 1</span>
              <Link href="/section2" className="site-topnav-link">
                Section 2
              </Link>
              <Link href="/section3" className="site-topnav-link">
                Section 3
              </Link>
            </div>
            <Link href="/#menu" className="site-topnav-action">
              Menu
            </Link>
          </div>
        ) : (
          <ArticleTopNav section={section} />
        )}

        <header className="section-landing-hero">
          <p>{`${getSectionLabel(section)} / ${section === "section1" ? "Interactive dashboards" : "Case writeups"}`}</p>
          <h1>{title}</h1>
          <span>{description}</span>
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
        </header>

        <div className="section-landing-grid section-landing-grid-sticky">
          {items.map((item, index) => (
            <Link
              key={item.slug}
              href={item.href}
              className={`compare-card section-landing-card section-landing-sticky-card section-landing-sticky-card-${index % 3}`}
            >
              <p>{item.kicker}</p>
              <h2>{item.title}</h2>
              <span>{item.description}</span>
              <div className="compare-card-footer">
                <b>{item.ctaLabel}</b>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </main>
  )
}
