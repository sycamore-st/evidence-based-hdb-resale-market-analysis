import { FilterRail } from "@/components/layout/filter-rail"
import { Sparkline } from "@/components/charts/sparkline"
import { Card } from "@/components/ui/card"
import { readDashboardBundle } from "@/lib/artifacts"

export default async function OverviewPage() {
  const bundle = await readDashboardBundle("overview")

  return (
    <div className="dashboard-grid">
      <section className="content-column">
        <header className="page-header">
          <p className="eyebrow">Market overview</p>
          <h2>{bundle.summary.headline}</h2>
          <p>{bundle.summary.description}</p>
        </header>

        <section className="card-grid">
          {bundle.summary.cards.map((card) => (
            <Card key={card.id}>
              <p className="eyebrow">{card.label}</p>
              <h3>{card.value}</h3>
              <p>{card.context}</p>
            </Card>
          ))}
        </section>

        <section className="chart-grid">
          {bundle.timeseries.series.map((series) => (
            <Card key={series.id}>
              <Sparkline series={series} />
            </Card>
          ))}
        </section>

        <Card>
          <p className="eyebrow">Artifact notes</p>
          <ul className="insight-list">
            {bundle.metadata.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </Card>
      </section>

      <FilterRail filters={bundle.filters} />
    </div>
  )
}
