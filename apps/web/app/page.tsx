export default function HomePage() {
  return (
    <main className="compare-page">
      <section className="compare-hero">
        <p className="compare-kicker">Homepage studies</p>
        <h1>Choose the visual direction before we redesign the real dashboard.</h1>
        <p>
          These are three actual homepage mockups inside `apps/web`, built to compare tone, layout, and credibility in
          the browser.
        </p>
      </section>

      <section className="compare-grid">
        <a className="compare-card compare-card-minimal" href="/section1/dashboard-1">
          <p>Working page</p>
          <h2>Dashboard 1 Port</h2>
          <span>First browser version of the actual country/town dashboard using the original screenshots.</span>
        </a>

        <a className="compare-card compare-card-editorial" href="/mockups/editorial">
          <p>Style A</p>
          <h2>Editorial Light</h2>
          <span>Best for narrative policy storytelling and a research-publication feel.</span>
        </a>

        <a className="compare-card compare-card-minimal" href="/mockups/minimal">
          <p>Style B</p>
          <h2>Data Product Minimal</h2>
          <span>Best for a serious, credible analytics product. This is still my recommended direction.</span>
        </a>

        <a className="compare-card compare-card-premium" href="/mockups/premium">
          <p>Style C</p>
          <h2>Premium Glass Light</h2>
          <span>Best if you want something more distinctive and demo-forward.</span>
        </a>
      </section>
    </main>
  )
}
