"use client"

import Link from "next/link"
import dynamic from "next/dynamic"
import { memo, useEffect, useMemo, useRef, useState, useTransition } from "react"
import type { CSSProperties } from "react"

import type { DashboardOneData, DashboardOneRow, MapShape } from "@/lib/section1-dashboard1"
import type { DashboardOneMapSide, DashboardOneRightPanel } from "@/lib/section1-dashboard1-sandbox"

const Plot = dynamic(() => import("@/components/charts/plotly-chart"), { ssr: false })

export type DashboardOneLayoutPreset = "editorial" | "balanced" | "chart-heavy"
export type DashboardOneStyleVars = Partial<Record<`--${string}`, string>>

const FLAT_COLORS: Record<string, string> = {
  "1 ROOM": "#8f9eaa",
  "2 ROOM": "#bfcfd7",
  "3 ROOM": "#b59995",
  "4 ROOM": "#d9c7aa",
  "5 ROOM": "#adbdad",
  EXECUTIVE: "#d9cedf",
  "MULTI-GENERATION": "#8b8fab",
}

const DEFAULT_FLAT_COLOR = "#d0d7dd"

function hexToRgb(hex: string): [number, number, number] {
  const normalized = hex.replace("#", "")
  const values = normalized.length === 3 ? normalized.split("").map((value) => value + value) : normalized.match(/.{1,2}/g)
  const [r, g, b] = (values ?? ["d0", "d7", "dd"]).slice(0, 3).map((value) => parseInt(value, 16))
  return [r, g, b]
}

function withAlpha(hex: string, alpha: number): string {
  const [r, g, b] = hexToRgb(hex)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function darken(hex: string, amount: number): string {
  const [r, g, b] = hexToRgb(hex)
  const clamp = (value: number) => Math.max(0, Math.min(255, Math.round(value * (1 - amount))))
  return `rgb(${clamp(r)}, ${clamp(g)}, ${clamp(b)})`
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-SG", {
    style: "currency",
    currency: "SGD",
    maximumFractionDigits: 0,
  }).format(value)
}

function seriesForSelection(rows: DashboardOneRow[], town: string | null, flatType: string) {
  const scopeTown = town ?? "NATIONAL"
  const scopedRows = rows.filter((row) => row.town === scopeTown)
  const seriesRows =
    flatType === "ALL FLAT TYPE" ? scopedRows.filter((row) => row.flatType !== "ALL FLAT TYPE") : scopedRows.filter((row) => row.flatType === flatType)

  const groups = new Map<string, DashboardOneRow[]>()
  for (const row of seriesRows) {
    if (row.transactions <= 0 && row.medianPrice <= 0) {
      continue
    }
    const list = groups.get(row.flatType) ?? []
    list.push(row)
    groups.set(row.flatType, list)
  }

  return Array.from(groups.entries())
    .map(([name, points]) => ({
      name,
      points: points.sort((left, right) => left.year - right.year),
      color: FLAT_COLORS[name] ?? DEFAULT_FLAT_COLOR,
      fillColor: withAlpha(FLAT_COLORS[name] ?? DEFAULT_FLAT_COLOR, 0.34),
      strokeColor: darken(FLAT_COLORS[name] ?? DEFAULT_FLAT_COLOR, 0.18),
    }))
    .sort((left, right) => left.name.localeCompare(right.name))
}

function mapMetrics(rows: DashboardOneRow[], year: number, flatType: string) {
  const filtered = rows.filter((row) => row.year === year && row.town !== "NATIONAL")
  const relevant = flatType === "ALL FLAT TYPE" ? filtered.filter((row) => row.flatType === "ALL FLAT TYPE") : filtered.filter((row) => row.flatType === flatType)

  return new Map(relevant.map((row) => [row.regionKey, row]))
}

function quantizedFill(value: number, min: number, max: number, isActive: boolean) {
  if (isActive) {
    return "#6f8f82"
  }
  if (!Number.isFinite(value) || value <= 0 || max <= min) {
    return "#f2efe9"
  }

  const ratio = (value - min) / (max - min)
  if (ratio < 0.2) return "#eef2ef"
  if (ratio < 0.4) return "#dde6df"
  if (ratio < 0.6) return "#c8d5cb"
  if (ratio < 0.8) return "#adc0b0"
  return "#8ea792"
}

const TownMap = memo(function TownMap({
  shapes,
  metrics,
  activeTown,
  onSelectTown,
}: {
  shapes: MapShape[]
  metrics: Map<string, DashboardOneRow>
  activeTown: string | null
  onSelectTown: (town: string | null) => void
}) {
  const values = Array.from(metrics.values()).map((row) => row.medianPrice).filter((value) => value > 0)
  const min = values.length > 0 ? Math.min(...values) : 0
  const max = values.length > 0 ? Math.max(...values) : 0

  return (
    <div className="dashboard1-map-shell">
      <svg viewBox="0 0 540 420" className="dashboard1-map" role="img" aria-label="Singapore HDB town map">
        {shapes.map((shape, index) => {
          const metric = metrics.get(shape.regionKey)
          const isActive = Boolean(activeTown && shape.town === activeTown)
          const clickable = Boolean(shape.town)
          return (
            <path
              key={`${shape.regionKey}-${index}`}
              d={shape.path}
              fill={quantizedFill(metric?.medianPrice ?? 0, min, max, isActive)}
              stroke={isActive ? "#617669" : "#cfd6d0"}
              strokeWidth={isActive ? 1.8 : 1}
              style={{ cursor: clickable ? "pointer" : "default" }}
              onClick={() => {
                if (!shape.town) return
                onSelectTown(activeTown === shape.town ? null : shape.town)
              }}
            />
          )
        })}
      </svg>

      <div className="dashboard1-map-legend">
        <span>Median Price</span>
        <div className="dashboard1-map-legend-bar" />
        <div className="dashboard1-map-legend-scale">
          <span>{formatCurrency(min || 0)}</span>
          <span>{formatCurrency(max || 0)}</span>
        </div>
      </div>
    </div>
  )
})

function StackedBarsPlot({
  series,
}: {
  series: Array<{
    name: string
    points: DashboardOneRow[]
    color: string
    fillColor: string
    strokeColor: string
  }>
}) {
  const shellRef = useRef<HTMLDivElement | null>(null)
  const [hoverState, setHoverState] = useState<{ x: number; left: number; top: number } | null>(null)
  const years = Array.from(new Set(series.flatMap((entry) => entry.points.map((point) => point.year)))).sort((a, b) => a - b)
  const plotKey = useMemo(
    () =>
      JSON.stringify(
        series.map((entry) => ({
          name: entry.name,
          years: entry.points.map((point) => point.year),
        })),
      ),
    [series],
  )

  useEffect(() => {
    setHoverState(null)
  }, [plotKey])

  const hoverBreakdown = useMemo(() => {
    if (!hoverState) {
      return null
    }
    const items = series
      .map((entry) => ({
        name: entry.name,
        fillColor: entry.fillColor,
        strokeColor: entry.strokeColor,
        value: entry.points.find((point) => point.year === hoverState.x)?.transactions ?? 0,
      }))
      .filter((item) => item.value > 0)
      .sort((left, right) => right.value - left.value)
    if (items.length === 0) {
      return null
    }
    const total = items.reduce((sum, item) => sum + item.value, 0)
    const itemsWithShare = items.map((item) => ({
      ...item,
      share: total > 0 ? (item.value / total) * 100 : 0,
    }))
    return { year: hoverState.x, left: hoverState.left, top: hoverState.top, items: itemsWithShare, total }
  }, [hoverState, series])

  const traces = series.map((entry) => ({
    type: "bar" as const,
    name: entry.name,
    x: years,
    y: years.map((year) => entry.points.find((point) => point.year === year)?.transactions ?? 0),
    marker: {
      color: entry.fillColor,
      line: {
        color: entry.strokeColor,
        width: 1.2,
      },
    },
    hoverinfo: "none" as const,
  }))

  return (
    <div className="dashboard1-chart-shell" ref={shellRef} onMouseLeave={() => setHoverState(null)}>
      <div className="dashboard1-chart-header">
        <h3>Transactions over time</h3>
        <span>Stacked by flat type</span>
      </div>
      <Plot
        key={plotKey}
        data={traces}
        layout={{
          autosize: true,
          barmode: "stack",
          showlegend: false,
          margin: { l: 68, r: 24, t: 8, b: 48 },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          hovermode: "x",
          font: { family: '"Avenir Next", "Segoe UI", sans-serif', color: "rgba(38,35,31,0.78)", size: 12 },
          xaxis: {
            tickmode: "linear",
            dtick: 4,
            gridcolor: "rgba(87,78,65,0.08)",
            zeroline: false,
            title: { text: "Year of transaction year" },
          },
          yaxis: {
            rangemode: "tozero",
            separatethousands: true,
            gridcolor: "rgba(87,78,65,0.12)",
            zeroline: false,
            title: { text: "Transactions count" },
          },
        }}
        config={{
          displayModeBar: false,
          responsive: true,
        }}
        className="dashboard1-plot dashboard1-plot-bar"
        useResizeHandler
        style={{ width: "100%", height: "100%" }}
        onHover={(rawEvent) => {
          const event = rawEvent as {
            points?: Array<{ x?: number | string }>
            event?: { clientX?: number; clientY?: number }
          }
          const pointX = event.points?.[0]?.x
          const year = typeof pointX === "number" ? pointX : Number(pointX)
          if (!Number.isFinite(year) || !shellRef.current) {
            return
          }
          const box = shellRef.current.getBoundingClientRect()
          const clientX = event.event?.clientX ?? box.left + box.width * 0.66
          const clientY = event.event?.clientY ?? box.top + 70
          const left = Math.max(12, Math.min(box.width - 276, clientX - box.left + 14))
          const top = Math.max(12, Math.min(box.height - 232, clientY - box.top - 16))
          setHoverState({ x: year, left, top })
        }}
        onUnhover={() => {
          setHoverState(null)
        }}
      />
      {hoverBreakdown ? (
        <div
          className="dashboard1-hover-card"
          style={{ left: `${hoverBreakdown.left}px`, top: `${hoverBreakdown.top}px` }}
        >
          <div className="dashboard1-hover-card-head">
            <strong>{hoverBreakdown.year}</strong>
            <span>{hoverBreakdown.total.toLocaleString()} total</span>
          </div>
          <div className="dashboard1-hover-mini-bars">
            {hoverBreakdown.items.map((item) => (
              <div key={`${hoverBreakdown.year}-${item.name}`} className="dashboard1-hover-mini-row">
                <div className="dashboard1-hover-mini-label">{item.name}</div>
                <div className="dashboard1-hover-mini-track">
                  <span
                    className="dashboard1-hover-mini-fill"
                    style={{
                      width: `${Math.max(3, item.share)}%`,
                      background: item.fillColor,
                      border: `1px solid ${item.strokeColor}`,
                      boxSizing: "border-box",
                    }}
                  />
                </div>
                <div className="dashboard1-hover-mini-value">
                  {item.value.toLocaleString()} ({item.share.toFixed(1)}%)
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}

function PriceLinesPlot({
  series,
}: {
  series: Array<{
    name: string
    points: DashboardOneRow[]
    color: string
    fillColor: string
    strokeColor: string
  }>
}) {
  const years = Array.from(new Set(series.flatMap((entry) => entry.points.map((point) => point.year)))).sort((a, b) => a - b)
  const traces = series.map((entry) => ({
    type: "scatter" as const,
    mode: "lines+markers",
    name: entry.name,
    x: years,
    y: years.map((year) => entry.points.find((point) => point.year === year)?.medianPrice ?? null),
    line: {
      color: entry.strokeColor,
      width: 3,
      shape: "linear" as const,
    },
    marker: {
      color: entry.strokeColor,
      size: 6,
    },
    hovertemplate: `%{fullData.name}<br>%{x}: SGD %{y:,.0f}<extra></extra>`,
  }))

  return (
    <div className="dashboard1-chart-shell">
      <div className="dashboard1-chart-header">
        <h3>Median price over time</h3>
        <span>Linked to the same scope and flat type</span>
      </div>
      <Plot
        data={traces}
        layout={{
          autosize: true,
          showlegend: false,
          margin: { l: 84, r: 30, t: 8, b: 48 },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          font: { family: '"Avenir Next", "Segoe UI", sans-serif', color: "rgba(38,35,31,0.78)", size: 12 },
          xaxis: {
            tickmode: "linear",
            dtick: 4,
            gridcolor: "rgba(87,78,65,0.08)",
            zeroline: false,
            title: { text: "Year of transaction year" },
          },
          yaxis: {
            rangemode: "tozero",
            tickprefix: "SGD ",
            separatethousands: true,
            gridcolor: "rgba(87,78,65,0.12)",
            zeroline: false,
            title: { text: "Median median price" },
          },
          hoverlabel: {
            bgcolor: "#fffdf9",
            bordercolor: "rgba(87,78,65,0.18)",
            font: { color: "#26231f" },
          },
        }}
        config={{
          displayModeBar: false,
          responsive: true,
        }}
        className="dashboard1-plot dashboard1-plot-line"
        useResizeHandler
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  )
}

function Legend({
  series,
}: {
  series: Array<{ name: string; color: string; fillColor: string; strokeColor: string }>
}) {
  return (
    <div className="dashboard1-legend-list">
      {series.map((entry) => (
        <div key={entry.name} className="dashboard1-legend-row">
          <span
            className="dashboard1-legend-swatch"
            style={{ background: entry.fillColor, border: `1px solid ${entry.strokeColor}` }}
          />
          <span>{entry.name}</span>
        </div>
      ))}
    </div>
  )
}

export function DashboardOneExplorer({
  data,
  layoutPreset = "balanced",
  mapSide = "left",
  rightOrder = ["legend", "bars", "lines"],
  styleVars,
  layoutLinkBase = "/section1/dashboard-1",
}: {
  data: DashboardOneData
  layoutPreset?: DashboardOneLayoutPreset
  mapSide?: DashboardOneMapSide
  rightOrder?: DashboardOneRightPanel[]
  styleVars?: DashboardOneStyleVars
  layoutLinkBase?: string
}) {
  const [selectedYear, setSelectedYear] = useState<number>(data.years[0] ?? 2026)
  const [selectedFlatType, setSelectedFlatType] = useState<string>("ALL FLAT TYPE")
  const [selectedTown, setSelectedTown] = useState<string | null>(null)
  const [, startTransition] = useTransition()

  const mapData = useMemo(
    () => mapMetrics(data.rows, selectedYear, selectedFlatType),
    [data.rows, selectedYear, selectedFlatType],
  )
  const series = useMemo(
    () => seriesForSelection(data.rows, selectedTown, selectedFlatType),
    [data.rows, selectedTown, selectedFlatType],
  )
  const activeScope = selectedTown ?? "NATIONAL"
  const summaryRow = useMemo(() => {
    const scopeRows = data.rows.filter(
      (row) => row.year === selectedYear && row.town === activeScope && row.flatType === selectedFlatType,
    )
    return (
      scopeRows[0] ??
      data.rows.find((row) => row.year === selectedYear && row.town === activeScope && row.flatType === "ALL FLAT TYPE")
    )
  }, [activeScope, data.rows, selectedFlatType, selectedYear])

  const normalizedRightOrder = useMemo<DashboardOneRightPanel[]>(() => {
    const allowed: DashboardOneRightPanel[] = ["legend", "bars", "lines"]
    const unique = rightOrder.filter(
      (item, index) => allowed.includes(item) && rightOrder.indexOf(item) === index,
    )
    const missing = allowed.filter((item) => !unique.includes(item))
    return [...unique, ...missing].slice(0, 3)
  }, [rightOrder])

  const areaByPanel = useMemo<Record<DashboardOneRightPanel, "legend" | "bars" | "lines">>(() => {
    const slots: Array<"legend" | "bars" | "lines"> = ["legend", "bars", "lines"]
    const mapped: Record<DashboardOneRightPanel, "legend" | "bars" | "lines"> = {
      legend: "legend",
      bars: "bars",
      lines: "lines",
    }
    normalizedRightOrder.forEach((panel, index) => {
      mapped[panel] = slots[index]
    })
    return mapped
  }, [normalizedRightOrder])

  const layoutHref = (layout: DashboardOneLayoutPreset) => {
    const params = new URLSearchParams()
    params.set("layout", layout)
    params.set("side", mapSide)
    params.set("order", normalizedRightOrder.join(","))
    return `${layoutLinkBase}?${params.toString()}`
  }

  return (
    <main className="dashboard1-page" style={styleVars as CSSProperties}>
      <header className="dashboard1-header">
        <div>
          <p className="dashboard1-kicker">Section 1 / Interactive Dashboard 1</p>
          <h1>How resale prices and demand vary across Singapore</h1>
          <p>
            Select a transaction year, choose a flat type, and click a town on the map to update the linked demand and
            price trends.
          </p>
        </div>
        <div className="dashboard1-header-actions">
          <div className="dashboard1-layout-switch">
            <span>Layout</span>
            <Link
              href={layoutHref("editorial") as never}
              className={layoutPreset === "editorial" ? "dashboard1-switch-link dashboard1-switch-link-active" : "dashboard1-switch-link"}
            >
              editorial
            </Link>
            <Link
              href={layoutHref("balanced") as never}
              className={layoutPreset === "balanced" ? "dashboard1-switch-link dashboard1-switch-link-active" : "dashboard1-switch-link"}
            >
              balanced
            </Link>
            <Link
              href={layoutHref("chart-heavy") as never}
              className={layoutPreset === "chart-heavy" ? "dashboard1-switch-link dashboard1-switch-link-active" : "dashboard1-switch-link"}
            >
              chart-heavy
            </Link>
          </div>
          <Link href="/" className="dashboard1-link">
            Back to index
          </Link>
          <Link href="/section1/dashboard-1/sandbox" className="dashboard1-link">
            Open sandbox
          </Link>
        </div>
      </header>

      <section className="dashboard1-controls">
        <label className="dashboard1-control">
          <span>1. Transaction year</span>
          <select value={selectedYear} onChange={(event) => setSelectedYear(Number(event.target.value))}>
            {data.years.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </label>

        <label className="dashboard1-control">
          <span>2. Flat type</span>
          <select value={selectedFlatType} onChange={(event) => setSelectedFlatType(event.target.value)}>
            {data.flatTypes.map((flatType) => (
              <option key={flatType} value={flatType}>
                {flatType}
              </option>
            ))}
          </select>
        </label>

        <div className="dashboard1-control dashboard1-control-scope">
          <span>3. Selected scope</span>
          <strong>{activeScope}</strong>
          <button
            type="button"
            onClick={() => {
              startTransition(() => setSelectedTown(null))
            }}
            disabled={selectedTown === null}
          >
            Reset to country view
          </button>
        </div>

        <div className="dashboard1-control dashboard1-control-summary">
          <span>Current snapshot</span>
          <strong>{summaryRow ? formatCurrency(summaryRow.medianPrice) : "No data"}</strong>
          <small>
            {summaryRow ? `${summaryRow.transactions.toLocaleString()} transactions in ${selectedYear}` : "No data for this selection."}
          </small>
        </div>
      </section>

      <section className={`dashboard1-layout dashboard1-layout-${layoutPreset} ${mapSide === "right" ? "dashboard1-layout-map-right" : ""}`}>
        <div className="dashboard1-map-panel dashboard1-panel-map">
          <div className="dashboard1-panel-header">
            <div>
              <p className="dashboard1-panel-label">3. Select a town on the map</p>
              <h2>{selectedTown ? `${selectedTown} selected` : "Country view"}</h2>
            </div>
            <span>{selectedFlatType}</span>
          </div>
          <TownMap
            shapes={data.mapShapes}
            metrics={mapData}
            activeTown={selectedTown}
            onSelectTown={(town) => {
              startTransition(() => setSelectedTown(town))
            }}
          />
        </div>

        <div className="dashboard1-panel-legend" style={{ gridArea: areaByPanel.legend }}>
          <p className="dashboard1-panel-label">Legend / flat type</p>
          <Legend
            series={series.map((entry) => ({
              name: entry.name,
              color: entry.color,
              fillColor: entry.fillColor,
              strokeColor: entry.strokeColor,
            }))}
          />
        </div>

        <div className="dashboard1-panel-bars" style={{ gridArea: areaByPanel.bars }}>
          <StackedBarsPlot series={series} />
        </div>

        <div className="dashboard1-panel-lines" style={{ gridArea: areaByPanel.lines }}>
          <PriceLinesPlot series={series} />
        </div>
      </section>
    </main>
  )
}
