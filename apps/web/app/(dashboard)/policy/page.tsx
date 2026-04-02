import { BarChart } from "@/components/charts/bar-chart"
import { FilterRail } from "@/components/layout/filter-rail"
import { Card } from "@/components/ui/card"
import { readDashboardBundle } from "@/lib/artifacts"

export default async function PolicyPage() {
  const bundle = await readDashboardBundle("policy")

  return (
    <div className="dashboard-grid">
      <section className="content-column">
        <header className="page-header">
          <p className="eyebrow">Policy analysis</p>
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
              <BarChart series={series} />
            </Card>
          ))}
        </section>

        <Card>
          <p className="eyebrow">Key takeaways</p>
          <ul className="insight-list">
            {bundle.summary.insights.map((insight) => (
              <li key={insight}>{insight}</li>
            ))}
          </ul>
        </Card>
      </section>

      <FilterRail filters={bundle.filters} />
    </div>
  )
}
