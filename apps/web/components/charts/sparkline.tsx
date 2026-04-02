import type { ChartSeries } from "@/lib/artifacts"

function buildPolyline(series: ChartSeries, width: number, height: number): string {
  if (series.points.length === 0) {
    return ""
  }

  const values = series.points.map((point) => point.y)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1

  return series.points
    .map((point, index) => {
      const x = (index / Math.max(series.points.length - 1, 1)) * width
      const y = height - ((point.y - min) / range) * height
      return `${x},${y}`
    })
    .join(" ")
}

export function Sparkline({ series }: { series: ChartSeries }) {
  const polyline = buildPolyline(series, 320, 120)

  return (
    <div className="chart-shell">
      <div className="chart-header">
        <h3>{series.label}</h3>
        <span>{series.points.at(-1)?.x ?? "No data"}</span>
      </div>
      <svg viewBox="0 0 320 120" className="sparkline" role="img" aria-label={series.label}>
        <polyline points={polyline} fill="none" stroke="var(--primary)" strokeWidth="4" strokeLinecap="round" />
      </svg>
      <div className="chart-axis">
        {series.points.map((point) => (
          <span key={point.x}>{point.x}</span>
        ))}
      </div>
    </div>
  )
}
