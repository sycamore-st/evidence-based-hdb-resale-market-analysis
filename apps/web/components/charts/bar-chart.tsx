import type { ChartSeries } from "@/lib/artifacts"

export function BarChart({ series }: { series: ChartSeries }) {
  const max = Math.max(...series.points.map((point) => point.y), 1)

  return (
    <div className="chart-shell">
      <div className="chart-header">
        <h3>{series.label}</h3>
        <span>{series.points.length} points</span>
      </div>
      <div className="bar-grid">
        {series.points.map((point) => (
          <div key={point.x} className="bar-row">
            <div className="bar-meta">
              <strong>{point.x}</strong>
              <span>{point.y.toFixed(1)}</span>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${(point.y / max) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
