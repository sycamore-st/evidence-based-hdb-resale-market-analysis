"use client"

import Link from "next/link"
import { memo, useMemo, useState, useTransition } from "react"
import type { CSSProperties } from "react"

import {
  formatSectionCurrency,
  SECTION1_CONTROL_LABELS,
  SECTION1_FLAT_COLORS,
  SectionDashboardNav,
} from "@/components/section1/dashboard-shared"
import { SectionTrendPriceLines, SectionTrendStackedBars } from "@/components/section1/dashboard-trend-charts"
import type { DashboardOneData, DashboardOneRow, MapShape } from "@/lib/section1-dashboard1"

export type DashboardOneLayoutPreset = "editorial" | "balanced" | "chart-heavy" | "map-heavy" | "stacked"
export type DashboardOneStyleVars = Partial<Record<`--${string}`, string>>
export type DashboardOneMapSide = "left" | "right"
export type DashboardOneRightPanel = "legend" | "bars" | "lines"

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
      color: SECTION1_FLAT_COLORS[name] ?? DEFAULT_FLAT_COLOR,
      fillColor: withAlpha(SECTION1_FLAT_COLORS[name] ?? DEFAULT_FLAT_COLOR, 0.34),
      strokeColor: darken(SECTION1_FLAT_COLORS[name] ?? DEFAULT_FLAT_COLOR, 0.18),
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
          <span>{formatSectionCurrency(min || 0)}</span>
          <span>{formatSectionCurrency(max || 0)}</span>
        </div>
      </div>
    </div>
  )
})

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
            <Link
              href={layoutHref("map-heavy") as never}
              className={layoutPreset === "map-heavy" ? "dashboard1-switch-link dashboard1-switch-link-active" : "dashboard1-switch-link"}
            >
              map-heavy
            </Link>
            <Link
              href={layoutHref("stacked") as never}
              className={layoutPreset === "stacked" ? "dashboard1-switch-link dashboard1-switch-link-active" : "dashboard1-switch-link"}
            >
              stacked
            </Link>
          </div>
          <SectionDashboardNav current="dashboard-1" className="dashboard1-header-actions-links" />
        </div>
      </header>

      <section className="dashboard1-controls">
        <label className="dashboard1-control">
          <span>{`1. ${SECTION1_CONTROL_LABELS.transactionYear}`}</span>
          <select value={selectedYear} onChange={(event) => setSelectedYear(Number(event.target.value))}>
            {data.years.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </label>

        <label className="dashboard1-control">
          <span>{`2. ${SECTION1_CONTROL_LABELS.flatType}`}</span>
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
          <strong>{summaryRow ? formatSectionCurrency(summaryRow.medianPrice) : "No data"}</strong>
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
          <div className="dashboard1-chart-shell">
            <div className="dashboard1-chart-header">
              <h3>Transactions over time</h3>
              <span>Stacked by flat type</span>
            </div>
            <SectionTrendStackedBars
              history={series.flatMap((entry) =>
                entry.points.map((point) => ({
                  year: point.year,
                  flatType: entry.name,
                  transactions: point.transactions,
                  medianPrice: point.medianPrice,
                })),
              )}
              colors={SECTION1_FLAT_COLORS}
              className="dashboard1-bars"
            />
          </div>
        </div>

        <div className="dashboard1-panel-lines" style={{ gridArea: areaByPanel.lines }}>
          <div className="dashboard1-chart-shell">
            <div className="dashboard1-chart-header">
              <h3>Median price over time</h3>
              <span>Linked to the same scope and flat type</span>
            </div>
            <SectionTrendPriceLines
              history={series.flatMap((entry) =>
                entry.points.map((point) => ({
                  year: point.year,
                  flatType: entry.name,
                  transactions: point.transactions,
                  medianPrice: point.medianPrice,
                })),
              )}
              colors={SECTION1_FLAT_COLORS}
              className="dashboard1-lines"
            />
          </div>
        </div>
      </section>
    </main>
  )
}
