"use client"

import { useMemo, useRef, useState } from "react"
import type { MouseEvent } from "react"

import { DashboardPager, formatSectionCurrency, SECTION1_CONTROL_LABELS, SectionDashboardNav } from "@/components/section1/dashboard-shared"
import type { DashboardTwoData, DashboardTwoMetricRow, DashboardTwoRow } from "@/lib/section1-dashboard2"

function extent(values: number[]) {
  const positive = values.filter((value) => value > 0)
  if (positive.length === 0) {
    return { min: 0, max: 1 }
  }
  return {
    min: Math.min(...positive),
    max: Math.max(...positive),
  }
}

function scale(value: number, min: number, max: number) {
  if (max <= min) return 0
  return ((value - min) / (max - min)) * 100
}

function axisTicks(min: number, max: number, segments: number) {
  if (segments <= 0) return [min, max]
  const step = (max - min) / segments
  return Array.from({ length: segments + 1 }, (_, index) => min + step * index)
}

function sortRows(rows: DashboardTwoRow[]) {
  const grouped = new Map<string, DashboardTwoRow[]>()
  for (const row of rows) {
    const list = grouped.get(row.town) ?? []
    list.push(row)
    grouped.set(row.town, list)
  }

  return Array.from(grouped.entries())
    .map(([town, items]) => ({
      town,
      items: items.sort((left, right) => right.medianFloorArea - left.medianFloorArea || right.medianPrice - left.medianPrice),
      topSize: Math.max(...items.map((item) => item.medianFloorArea)),
    }))
    .sort((left, right) => right.topSize - left.topSize || left.town.localeCompare(right.town))
}

function RangeGlyph({
  min,
  median,
  max,
  domainMin,
  domainMax,
  kind,
  onHover,
  onLeave,
}: {
  min: number
  median: number
  max: number
  domainMin: number
  domainMax: number
  kind: "area" | "price"
  onHover: (event: MouseEvent<HTMLDivElement>) => void
  onLeave: () => void
}) {
  const minX = scale(min, domainMin, domainMax)
  const medianX = scale(median, domainMin, domainMax)
  const maxX = scale(max, domainMin, domainMax)

  return (
    <div className={`dashboard2-range dashboard2-range-${kind}`} onMouseEnter={onHover} onMouseMove={onHover} onMouseLeave={onLeave}>
      <div className="dashboard2-range-track" />
      <div className="dashboard2-range-line" style={{ left: `${minX}%`, width: `${Math.max(1, maxX - minX)}%` }} />
      <span className="dashboard2-range-dot dashboard2-range-dot-median" style={{ left: `${medianX}%` }} />
    </div>
  )
}

export function DashboardTwoExplorer({ data }: { data: DashboardTwoData }) {
  const [selectedYear, setSelectedYear] = useState<number>(2026)
  const [selectedBudget, setSelectedBudget] = useState<number>(800000)
  const [selectedTowns, setSelectedTowns] = useState<string[]>(["ALL"])
  const [townPickerOpen, setTownPickerOpen] = useState(false)
  const [hoverState, setHoverState] = useState<{
    left: number
    top: number
    title: string
    subtitle: string
    rows: Array<{ label: string; value: string }>
  } | null>(null)
  const tableRef = useRef<HTMLDivElement | null>(null)

  const allTownsSelected = selectedTowns.length === 0 || selectedTowns.includes("ALL")
  const townSummary = allTownsSelected ? "ALL" : selectedTowns.length === 1 ? selectedTowns[0] : `${selectedTowns.length} towns selected`

  const filteredRows = useMemo(
    () =>
      data.rows.filter(
        (row) => row.year === selectedYear && row.budget === selectedBudget && (allTownsSelected || selectedTowns.includes(row.town)),
      ),
    [allTownsSelected, data.rows, selectedBudget, selectedTowns, selectedYear],
  )

  const metricLookup = useMemo(() => {
    const lookup = new Map<string, DashboardTwoMetricRow[]>()
    for (const row of data.metricRows) {
      if (row.year !== selectedYear || row.budget !== selectedBudget) continue
      const key = `${row.town}__${row.flatType}`
      const list = lookup.get(key) ?? []
      list.push(row)
      lookup.set(key, list)
    }
    return lookup
  }, [data.metricRows, selectedBudget, selectedYear])

  const groupedRows = useMemo(() => sortRows(filteredRows), [filteredRows])
  const visibleGroups = allTownsSelected ? groupedRows.slice(0, 10) : groupedRows
  const visibleRows = visibleGroups.flatMap((group) => group.items)

  const floorDomain = useMemo(
    () => extent(visibleRows.flatMap((row) => [row.minFloorArea, row.medianFloorArea, row.maxFloorArea])),
    [visibleRows],
  )
  const priceDomain = useMemo(
    () => extent(visibleRows.flatMap((row) => [row.minPrice, row.medianPrice, row.maxPrice])),
    [visibleRows],
  )

  const floorTicks = axisTicks(Math.floor(floorDomain.min / 20) * 20, Math.ceil(floorDomain.max / 20) * 20, 8)
  const priceTickMax = Math.ceil(priceDomain.max / 500000) * 500000
  const priceTicks = axisTicks(0, priceTickMax, 3)
  const topRow = visibleRows[0] ?? null

  const toggleTown = (town: string) => {
    if (town === "ALL") {
      setSelectedTowns(["ALL"])
      return
    }
    setSelectedTowns((previous) => {
      const current = previous.includes("ALL") ? [] : previous
      const next = current.includes(town) ? current.filter((value) => value !== town) : [...current, town]
      return next.length === 0 ? ["ALL"] : next.sort((left, right) => left.localeCompare(right))
    })
  }

  const setHoverCard = (event: MouseEvent<HTMLDivElement>, row: DashboardTwoRow, kind: "area" | "price") => {
    if (!tableRef.current) return
    const box = tableRef.current.getBoundingClientRect()
    const cardWidth = 236
    const cardHeight = 196
    const pointerX = event.clientX
    const pointerY = event.clientY
    const nextLeft =
      pointerX + 10 + cardWidth <= box.width - 12
        ? pointerX + 10
        : Math.max(12, pointerX - cardWidth - 10)
    const nextTop =
      pointerY + 14 + cardHeight <= box.height - 12
        ? pointerY + 14
        : Math.max(12, pointerY - cardHeight - 10)
    const order = ["Min", "P25", "Median", "P75", "Max"]
    const rows = (metricLookup.get(`${row.town}__${row.flatType}`) ?? [])
      .sort((left, right) => order.indexOf(left.metric) - order.indexOf(right.metric))
      .map((item) => ({
        label: item.metric,
        value: kind === "area" ? `${item.floorArea.toFixed(0)} sqm` : formatSectionCurrency(item.price),
      }))

    setHoverState({
      left: nextLeft,
      top: Math.max(12, nextTop),
      title: `${row.town} / ${row.flatType}`,
      subtitle: kind === "area" ? "Floor area distribution" : "Price distribution",
      rows,
    })
  }

  return (
    <main className="dashboard2-page">
      <header className="dashboard2-header">
        <div>
          <p className="dashboard2-kicker">Section 1 / Interactive Dashboard 2</p>
          <h1>Buyer Budget Planner</h1>
          <p>
            Find towns and flat types that offer the most space within your budget, while comparing typical resale prices.
          </p>
        </div>
        <div className="dashboard2-header-actions">
          <SectionDashboardNav className="dashboard2-header-actions-links" />
        </div>
      </header>

      <section className="dashboard2-controls">
        <label className="dashboard2-control">
          <span className="dashboard2-control-label">
            {`1. ${SECTION1_CONTROL_LABELS.transactionYear}`}
            <span className="dashboard1-info-trigger" aria-label="Info">
              i
              <span className="dashboard1-info-tooltip">Filters the table to transactions from this year. Choose the year that matches your buying timeline.</span>
            </span>
          </span>
          <select value={selectedYear} onChange={(event) => setSelectedYear(Number(event.target.value))}>
            {data.years.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </label>

        <label className="dashboard2-control">
          <span className="dashboard2-control-label">
            {`2. ${SECTION1_CONTROL_LABELS.budget}`}
            <span className="dashboard1-info-trigger" aria-label="Info">
              i
              <span className="dashboard1-info-tooltip">Choose the budget tier that reflects your target shortlist. Only combinations at or below this price appear.</span>
            </span>
          </span>
          <select value={selectedBudget} onChange={(event) => setSelectedBudget(Number(event.target.value))}>
            {data.budgets.map((budget) => (
              <option key={budget} value={budget}>
                {formatSectionCurrency(budget)}
              </option>
            ))}
          </select>
        </label>

        <div className="dashboard2-control dashboard2-control-towns">
          <span className="dashboard2-control-label">
            {`3. ${SECTION1_CONTROL_LABELS.town}`}
            <span className="dashboard1-info-trigger" aria-label="Info">
              i
              <span className="dashboard1-info-tooltip">Select one or more towns to compare, or keep ALL for the broad comparison set.</span>
            </span>
          </span>
          <button type="button" className="dashboard2-multiselect-button" onClick={() => setTownPickerOpen((open) => !open)}>
            <strong>{townSummary}</strong>
            <span>{townPickerOpen ? "Hide" : "Choose"}</span>
          </button>
          {townPickerOpen ? (
            <div className="dashboard2-multiselect-menu">
              <label className="dashboard2-multiselect-option">
                <input type="checkbox" checked={allTownsSelected} onChange={() => toggleTown("ALL")} />
                <span>ALL</span>
              </label>
              {data.towns.map((town) => (
                <label key={town} className="dashboard2-multiselect-option">
                  <input type="checkbox" checked={!allTownsSelected && selectedTowns.includes(town)} onChange={() => toggleTown(town)} />
                  <span>{town}</span>
                </label>
              ))}
            </div>
          ) : null}
        </div>

        <div className="dashboard2-control dashboard2-control-summary">
          <span className="dashboard2-control-label">
            Current best space
            <span className="dashboard1-info-trigger" aria-label="Info">
              i
              <span className="dashboard1-info-tooltip">Hover any row to inspect Min, P25, Median, P75, and Max values. The range line shows the spread and the hollow dot marks the median.</span>
            </span>
          </span>
          <strong>{topRow ? `${topRow.town} / ${topRow.flatType}` : "No data"}</strong>
          <small>
            {topRow ? `${topRow.medianFloorArea.toFixed(0)} sqm median area at ${formatSectionCurrency(topRow.medianPrice)}` : "No combinations for this selection."}
          </small>
        </div>
      </section>

      <section className="dashboard2-layout">
        <div className="dashboard2-table-card" ref={tableRef}>
          <div className="dashboard2-chart-header">
            <p>Each row compares one town and flat type within your budget and year. The line shows the min-to-max range, and the hollow dot marks the median. Hover any row for the full five-number summary.</p>
            <div className="dashboard2-inline-legend">
              <div className="dashboard2-guide-swatch">
                <span className="dashboard2-range-dot dashboard2-range-dot-median" />
              </div>
              <div className="dashboard2-guide-labels">
                <span>Range</span>
                <span>Median</span>
              </div>
            </div>
          </div>
          <div className="dashboard2-table-head">
            <div className="dashboard2-row-labels">
              <span>Town</span>
              <span>Flat Type</span>
            </div>
            <div className="dashboard2-metric-head">
              <span>Median Floor Area</span>
              <div className="dashboard2-axis">
                {floorTicks.map((tick) => (
                  <span key={`floor-${tick}`}>{Math.round(tick)}</span>
                ))}
              </div>
            </div>
            <div className="dashboard2-metric-head">
              <span>Median Price</span>
              <div className="dashboard2-axis">
                {priceTicks.map((tick) => (
                  <span key={`price-${tick}`}>{tick === 0 ? "$0" : formatSectionCurrency(tick)}</span>
                ))}
              </div>
            </div>
          </div>

          <div className="dashboard2-table-body">
            {visibleGroups.map((group) => (
              <div key={group.town} className="dashboard2-town-group">
                {group.items.map((row, index) => (
                  <div key={`${group.town}-${row.flatType}`} className="dashboard2-table-row">
                    <div className="dashboard2-town-cell">{index === 0 ? group.town : ""}</div>
                    <div className="dashboard2-flat-cell">{row.flatType}</div>
                    <div className="dashboard2-metric-cell">
                      <RangeGlyph
                        min={row.minFloorArea}
                        median={row.medianFloorArea}
                        max={row.maxFloorArea}
                        domainMin={floorTicks[0] ?? floorDomain.min}
                        domainMax={floorTicks[floorTicks.length - 1] ?? floorDomain.max}
                        kind="area"
                        onHover={(event) => setHoverCard(event, row, "area")}
                        onLeave={() => setHoverState(null)}
                      />
                    </div>
                    <div className="dashboard2-metric-cell">
                      <RangeGlyph
                        min={row.minPrice}
                        median={row.medianPrice}
                        max={row.maxPrice}
                        domainMin={0}
                        domainMax={priceTickMax}
                        kind="price"
                        onHover={(event) => setHoverCard(event, row, "price")}
                        onLeave={() => setHoverState(null)}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>

          {hoverState ? (
            <div className="dashboard2-hover-card" style={{ left: `${hoverState.left}px`, top: `${hoverState.top}px` }}>
              <div className="dashboard2-hover-card-head">
                <strong>{hoverState.title}</strong>
                <span>{hoverState.subtitle}</span>
              </div>
              <div className="dashboard2-hover-card-body">
                {hoverState.rows.map((item) => (
                  <div key={`${hoverState.title}-${item.label}`} className="dashboard2-hover-card-row">
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

      </section>

      <DashboardPager current="/section1/dashboard-2" />
    </main>
  )
}
