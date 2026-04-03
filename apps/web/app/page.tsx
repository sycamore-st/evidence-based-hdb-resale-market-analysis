export default function HomePage() {
  return (
    <main className="compare-page">
      <section className="compare-hero">
        <p className="compare-kicker">Section 1 dashboards</p>
        <h1>Open the working web ports for the HDB resale dashboard set.</h1>
        <p>
          These pages move the original Tableau dashboard workflows into the browser while keeping the light editorial
          style used for Dashboard 1.
        </p>
      </section>

      <section className="compare-grid">
        <a className="compare-card compare-card-minimal" href="/section1/dashboard-1">
          <p>Working page</p>
          <h2>Dashboard 1 Port</h2>
          <span>First browser version of the actual country/town dashboard using the original screenshots.</span>
        </a>

        <a className="compare-card compare-card-minimal" href="/section1/dashboard-2">
          <p>Working page</p>
          <h2>Dashboard 2 Port</h2>
          <span>Budget-to-space comparison table ported to the web with the same editorial light styling.</span>
        </a>

        <a className="compare-card compare-card-minimal" href="/section1/dashboard-3">
          <p>Working page</p>
          <h2>Dashboard 3 Port</h2>
          <span>Budget-and-location shortlist with town-sharded JSON loading instead of the heavy Tableau workbook.</span>
        </a>
      </section>
    </main>
  )
}
