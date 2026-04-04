import Link from "next/link"

export default function HomePage() {
  return (
    <main className="compare-page">
      <section className="compare-stage">
        <header className="compare-topbar">
          <p className="compare-brand">HDB Resale Market Analysis</p>
          <div className="compare-topnav">
            <span>Section 1</span>
            <span>Interactive Dashboards</span>
            <span>Web Port</span>
          </div>
        </header>

        <section className="compare-hero">
          <div className="compare-hero-copy">
            <p className="compare-kicker">Section 1 dashboards</p>
            <h1>Explore the HDB resale dashboard set in the browser.</h1>
            <p>
              A cleaner editorial landing page for the working web ports: market overview, budget comparison, and
              building-level shortlist exploration.
            </p>
          </div>

          <div className="compare-cards-scene">
            <Link
              className="compare-card compare-card-dashboard2 compare-card-back"
              href="/section1/dashboard-2"
              title="Open Dashboard 2: budget to space comparison across towns and flat types"
              aria-label="Open Dashboard 2: budget to space comparison across towns and flat types"
            >
              <p>Interactive dashboard</p>
              <h2>Buyer Budget Planner</h2>
              <span>Budget-to-space comparison across towns and flat types with range hover details.</span>
              <div className="compare-card-footer">
                <b>Open Dashboard 2</b>
                <small>Range comparison, hover details</small>
              </div>
            </Link>

            <Link
              className="compare-card compare-card-dashboard1 compare-card-front"
              href="/section1/dashboard-1"
              title="Open Dashboard 1: country and town overview with linked map and trends"
              aria-label="Open Dashboard 1: country and town overview with linked map and trends"
            >
              <p>Interactive dashboard</p>
              <h2>How resale prices and demand vary across Singapore.</h2>
              <span>Country and town view with linked map, transaction volume, and median price trends.</span>
              <div className="compare-card-footer">
                <b>Open Dashboard 1</b>
                <small>Map, transactions, price trend</small>
              </div>
            </Link>

            <Link
              className="compare-card compare-card-dashboard3 compare-card-float"
              href="/section1/dashboard-3"
              title="Open Dashboard 3: building shortlist, nearby amenities, and linked trends"
              aria-label="Open Dashboard 3: building shortlist, nearby amenities, and linked trends"
            >
              <p>Interactive dashboard</p>
              <h2>Find Flats by Budget and Location.</h2>
              <span>Building shortlist with geometry, nearby amenities, and linked trend context.</span>
              <div className="compare-card-footer">
                <b>Open Dashboard 3</b>
                <small>Buildings, POIs, linked trends</small>
              </div>
            </Link>
          </div>
        </section>
      </section>
    </main>
  )
}
