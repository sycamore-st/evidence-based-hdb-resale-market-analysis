import Link from "next/link"

import { MENU_PAGE_ROWS } from "@/lib/sections"

export function HomePageShell() {
  return (
    <main className="compare-page">
      <section className="compare-stage">
        <header className="compare-topbar">
          <p className="compare-brand">HDB Resale Market Analysis</p>
          <div className="compare-topnav">
            <a href="#landing">Landing</a>
            <a href="#menu">Menu</a>
            <Link href="/section1">Section 1</Link>
            <Link href="/section2">Section 2</Link>
            <Link href="/section3">Section 3</Link>
          </div>
        </header>

        <section id="landing" className="compare-hero compare-anchor-section">
          <div className="compare-hero-copy">
            <p className="compare-kicker">Section index</p>
            <h1>Browse the full HDB resale analysis by section.</h1>
            <p>
              Move from the shared landing page into interactive dashboards, predictive case work, and policy-oriented
              market analysis without losing the editorial flow of the project.
            </p>
          </div>

          <div className="compare-cards-scene">
            <Link className="compare-card compare-card-dashboard2 compare-card-back" href="/section2">
              <p>Case writeups</p>
              <h2>Section 2</h2>
              <span>Predictive modeling, valuation logic, and hidden-feature recovery studies.</span>
              <div className="compare-card-footer">
                <b>Open Section 2</b>
                <small>Prediction, valuation, recovery</small>
              </div>
            </Link>

            <Link className="compare-card compare-card-dashboard1 compare-card-front" href="/section1">
              <p>Interactive dashboards</p>
              <h2>Section 1</h2>
              <span>Market overview, buyer budget comparison, and building-level shortlist exploration.</span>
              <div className="compare-card-footer">
                <b>Open Section 1</b>
                <small>Overview, budget, location</small>
              </div>
            </Link>

            <Link className="compare-card compare-card-dashboard3 compare-card-float" href="/section3">
              <p>Policy notes</p>
              <h2>Section 3</h2>
              <span>Town comparisons, transport effects, size trends, and policy-facing interpretation.</span>
              <div className="compare-card-footer">
                <b>Open Section 3</b>
                <small>Towns, transit, policy</small>
              </div>
            </Link>
          </div>
        </section>

        <section id="menu" className="menu-page compare-anchor-section" aria-label="Menu page">
          {MENU_PAGE_ROWS.map((row) => (
            <div key={row.section} className="menu-row">
              <div className="menu-row-header">
                <p>{row.title}</p>
              </div>

              <div className="menu-row-grid">
                {row.cards.map((card) => (
                  <Link key={card.href} href={card.href} className="menu-card">
                    <div className="menu-card-head">
                      <p>{card.label}</p>
                      <span />
                    </div>
                    <div className="menu-card-copy">
                      <h2>{card.pageTitle}</h2>
                      <span>{card.description}</span>
                      <strong>Open page</strong>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </section>
      </section>
    </main>
  )
}
