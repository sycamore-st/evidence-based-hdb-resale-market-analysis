import Link from "next/link"

type MockStyle = "editorial" | "minimal" | "premium"

function EditorialMockup() {
  return (
    <div className="mock-editorial">
      <header className="editorial-topbar">
        <Link href="/" className="editorial-backlink">
          Compare styles
        </Link>
        <div className="editorial-meta">
          <span>Research-led dashboard study</span>
          <span>Edition 01</span>
        </div>
      </header>

      <main className="editorial-main">
        <section className="editorial-hero">
          <div className="editorial-headline">
            <p className="editorial-kicker">Style A / Editorial Light</p>
            <h1>Housing analysis that reads like a publication, not a tool.</h1>
            <p>
              This direction treats the homepage like a briefing note: a strong thesis, annotated evidence, and slower
              pacing that makes the policy analysis feel more intentional.
            </p>
          </div>
          <aside className="editorial-side-note">
            <p>Why it feels different</p>
            <strong>Story first, dashboard second.</strong>
            <span>The first screen is built to frame the narrative before the user gets into filtering.</span>
          </aside>
        </section>

        <section className="editorial-river">
          <article className="editorial-brief">
            <p className="editorial-section-label">Lead finding</p>
            <h2>Yishun looks more compelling as a value story than a cheapest-town story.</h2>
            <p>
              The layout leaves room for written interpretation beside the evidence, which is especially useful for
              Section 3 where the narrative matters as much as the chart.
            </p>
          </article>

          <article className="editorial-pull-quote">
            <span>Controlled effect</span>
            <strong>-21.1%</strong>
            <p>Relative to the reference town after controlling for type, age, and year.</p>
          </article>
        </section>

        <section className="editorial-columns">
          <article className="editorial-chart-card">
            <div className="editorial-chart-header">
              <h3>Market pace</h3>
              <span>Recent months</span>
            </div>
            <div className="editorial-line">
              <span style={{ height: "38%" }} />
              <span style={{ height: "42%" }} />
              <span style={{ height: "55%" }} />
              <span style={{ height: "63%" }} />
              <span style={{ height: "71%" }} />
              <span style={{ height: "82%" }} />
            </div>
            <div className="editorial-axis">
              <span>Oct</span>
              <span>Nov</span>
              <span>Dec</span>
              <span>Jan</span>
              <span>Feb</span>
              <span>Mar</span>
            </div>
          </article>

          <article className="editorial-notes-card">
            <p className="editorial-section-label">Reading rhythm</p>
            <ul>
              <li>Large headline area</li>
              <li>Interpretation blocks before data modules</li>
              <li>Feels strongest for policy and long-form findings</li>
            </ul>
          </article>
        </section>

        <section className="editorial-ledger">
          <article>
            <p className="editorial-section-label">Town snapshot</p>
            <div className="editorial-ledger-row">
              <span>QUEENSTOWN</span>
              <strong>SGD 698k</strong>
            </div>
            <div className="editorial-ledger-row">
              <span>TAMPINES</span>
              <strong>SGD 612k</strong>
            </div>
            <div className="editorial-ledger-row">
              <span>YISHUN</span>
              <strong>SGD 488k</strong>
            </div>
          </article>
          <article>
            <p className="editorial-section-label">Best use</p>
            <p>
              Best when you want the homepage to feel thoughtful, public-facing, and credible for explanatory policy
              work.
            </p>
          </article>
        </section>
      </main>
    </div>
  )
}

function MinimalMockup() {
  return (
    <div className="mock-minimal">
      <header className="minimal-header">
        <div>
          <p className="minimal-kicker">Style B / Data Product Minimal</p>
          <h1>Clean analytics product for fast reading.</h1>
        </div>
        <div className="minimal-header-actions">
          <Link href="/" className="minimal-link">
            Compare styles
          </Link>
          <span className="minimal-badge">Recommended</span>
        </div>
      </header>

      <main className="minimal-main">
        <aside className="minimal-filters">
          <p className="minimal-panel-label">Filters</p>
          <div className="minimal-filter-group">
            <strong>Town</strong>
            <span>YISHUN</span>
            <span>QUEENSTOWN</span>
            <span>TAMPINES</span>
          </div>
          <div className="minimal-filter-group">
            <strong>Flat type</strong>
            <span>3 ROOM</span>
            <span>4 ROOM</span>
            <span>5 ROOM</span>
          </div>
          <div className="minimal-filter-group">
            <strong>Surface</strong>
            <span>Overview</span>
            <span>Policy</span>
            <span>Model</span>
          </div>
        </aside>

        <section className="minimal-content">
          <div className="minimal-kpis">
            <article className="minimal-kpi">
              <p>Median price</p>
              <strong>SGD 545k</strong>
            </article>
            <article className="minimal-kpi">
              <p>Transactions</p>
              <strong>2,180</strong>
            </article>
            <article className="minimal-kpi">
              <p>Policy effect</p>
              <strong>-21.1%</strong>
            </article>
            <article className="minimal-kpi">
              <p>Model accuracy</p>
              <strong>98.4%</strong>
            </article>
          </div>

          <section className="minimal-core-grid">
            <article className="minimal-panel minimal-chart-panel">
              <div className="minimal-panel-header">
                <h2>Resale momentum</h2>
                <span>Stable 6-month trend</span>
              </div>
              <div className="minimal-bars">
                <span style={{ height: "44%" }} />
                <span style={{ height: "46%" }} />
                <span style={{ height: "58%" }} />
                <span style={{ height: "66%" }} />
                <span style={{ height: "74%" }} />
                <span style={{ height: "86%" }} />
              </div>
            </article>

            <article className="minimal-panel minimal-insight-panel">
              <div className="minimal-panel-header">
                <h2>Why this style works</h2>
                <span>Product mindset</span>
              </div>
              <ul>
                <li>Most credible for an actual dashboard</li>
                <li>Charts dominate instead of decorative surfaces</li>
                <li>Easy to scale into real pages and filters</li>
              </ul>
            </article>
          </section>

          <section className="minimal-bottom-grid">
            <article className="minimal-panel">
              <div className="minimal-panel-header">
                <h2>Town comparison</h2>
                <span>Compact module</span>
              </div>
              <div className="minimal-table-row">
                <span>QUEENSTOWN</span>
                <strong>698k</strong>
              </div>
              <div className="minimal-table-row">
                <span>TAMPINES</span>
                <strong>612k</strong>
              </div>
              <div className="minimal-table-row">
                <span>YISHUN</span>
                <strong>488k</strong>
              </div>
            </article>

            <article className="minimal-panel">
              <div className="minimal-panel-header">
                <h2>Personality</h2>
                <span>No drama</span>
              </div>
              <p>
                Feels like the front door of a serious analytics product. This is the most practical base for the real
                app.
              </p>
            </article>
          </section>
        </section>
      </main>
    </div>
  )
}

function PremiumMockup() {
  return (
    <div className="mock-premium">
      <header className="premium-nav">
        <Link href="/" className="premium-link">
          Compare styles
        </Link>
        <div className="premium-nav-links">
          <span>Overview</span>
          <span>Signals</span>
          <span>Scenarios</span>
        </div>
      </header>

      <main className="premium-main">
        <section className="premium-stage">
          <div className="premium-stage-copy">
            <p className="premium-kicker">Style C / Premium Interactive</p>
            <h1>HDB Resale Intelligence</h1>
            <p>
              A more cinematic direction for a showcase app: bold hero composition, layered surfaces, and stronger
              visual identity than a traditional dashboard.
            </p>
            <div className="premium-actions">
              <span className="premium-pill">Market</span>
              <span className="premium-pill">Policy</span>
              <span className="premium-pill">Model</span>
            </div>
          </div>

          <div className="premium-stage-card">
            <div className="premium-orb premium-orb-a" />
            <div className="premium-orb premium-orb-b" />
            <div className="premium-hero-metric">
              <span>Latest pulse</span>
              <strong>SGD 545k</strong>
              <p>Current median resale price from the published monthly artifact.</p>
            </div>
          </div>
        </section>

        <section className="premium-band">
          <article className="premium-panel premium-stat-ribbon">
            <div>
              <span>Transactions</span>
              <strong>2,180</strong>
            </div>
            <div>
              <span>Policy effect</span>
              <strong>-21.1%</strong>
            </div>
            <div>
              <span>Model accuracy</span>
              <strong>98.4%</strong>
            </div>
          </article>
        </section>

        <section className="premium-grid">
          <article className="premium-panel premium-chart-panel">
            <div className="premium-panel-header">
              <h2>Momentum wave</h2>
              <span>Visual-first module</span>
            </div>
            <div className="premium-wave">
              <span style={{ height: "28%" }} />
              <span style={{ height: "40%" }} />
              <span style={{ height: "56%" }} />
              <span style={{ height: "72%" }} />
              <span style={{ height: "88%" }} />
            </div>
          </article>

          <article className="premium-panel premium-copy-panel">
            <div className="premium-panel-header">
              <h2>Why it stands out</h2>
              <span>Demo energy</span>
            </div>
            <ul>
              <li>Most memorable in a portfolio or showcase setting</li>
              <li>Best if you want the app to feel premium on first glance</li>
              <li>Higher risk of looking too designed if overused</li>
            </ul>
          </article>

          <article className="premium-panel premium-stack-panel">
            <p className="premium-mini-label">Layered module</p>
            <strong>Town spotlight</strong>
            <span>YISHUN / 4 ROOM / 2026-03</span>
          </article>
        </section>
      </main>
    </div>
  )
}

export function HomepageMockup({ style }: { style: MockStyle }) {
  if (style === "editorial") {
    return <EditorialMockup />
  }

  if (style === "minimal") {
    return <MinimalMockup />
  }

  return <PremiumMockup />
}
