"use client"

import { useMemo, useRef, useState } from "react"

import { formatSectionCount, formatSectionCurrency } from "@/components/section1/dashboard-shared"

export type SectionTrendPoint = {
  year: number
  flatType: string
  transactions: number
  medianPrice: number
}

function buildHistoryMatrix(history: SectionTrendPoint[]) {
  const years = Array.from(new Set(history.map((item) => item.year))).sort((left, right) => left - right)
  const flatTypes = Array.from(new Set(history.map((item) => item.flatType))).sort((left, right) => left.localeCompare(right))
  const byYear = new Map<number, Map<string, SectionTrendPoint>>()

  for (const item of history) {
    if (!byYear.has(item.year)) {
      byYear.set(item.year, new Map())
    }
    byYear.get(item.year)?.set(item.flatType, item)
  }

  return { years, flatTypes, byYear }
}

export function SectionTrendStackedBars({
  history,
  colors,
  className = "section1-trend-bars",
}: {
  history: SectionTrendPoint[]
  colors: Record<string, string>
  className?: string
}) {
  const shellRef = useRef<HTMLDivElement | null>(null)
  const [hoverState, setHoverState] = useState<{ year: number; left: number; top: number } | null>(null)
  const { years, flatTypes, byYear } = useMemo(() => buildHistoryMatrix(history), [history])
  const totals = years.map((year) => flatTypes.map((flatType) => byYear.get(year)?.get(flatType)?.transactions ?? 0))
  const maxTotal = Math.max(...totals.map((values) => values.reduce((sum, value) => sum + value, 0)), 1)

  const hoverBreakdown = useMemo(() => {
    if (!hoverState) return null

    const items = flatTypes
      .map((flatType) => {
        const value = byYear.get(hoverState.year)?.get(flatType)?.transactions ?? 0
        return { name: flatType, value, color: colors[flatType] ?? "#b79f96" }
      })
      .filter((item) => item.value > 0)
      .sort((left, right) => right.value - left.value)

    if (items.length === 0) return null

    const total = items.reduce((sum, item) => sum + item.value, 0)
    return {
      ...hoverState,
      total,
      items: items.map((item) => ({
        ...item,
        share: total > 0 ? (item.value / total) * 100 : 0,
      })),
    }
  }, [byYear, colors, flatTypes, hoverState])

  return (
    <div className="section1-trend-shell" ref={shellRef} onMouseLeave={() => setHoverState(null)}>
      <div className={className}>
        {years.map((year, index) => {
          let offset = 0
          const yearValues = totals[index]
          const total = yearValues.reduce((sum, value) => sum + value, 0)

          return (
            <div
              key={year}
              className="section1-trend-bars-year"
              onMouseEnter={(event) => {
                const shell = shellRef.current
                if (!shell) return
                const shellRect = shell.getBoundingClientRect()
                const targetRect = event.currentTarget.getBoundingClientRect()
                setHoverState({
                  year,
                  left: Math.min(Math.max(targetRect.left - shellRect.left + targetRect.width * 0.72, 14), Math.max(shellRect.width - 286, 14)),
                  top: 14,
                })
              }}
            >
              <div className="section1-trend-bars-stack">
                {flatTypes.map((flatType, flatIndex) => {
                  const value = yearValues[flatIndex]
                  const height = total > 0 ? (value / maxTotal) * 100 : 0
                  const color = colors[flatType] ?? "#b79f96"
                  const segment = (
                    <span
                      key={flatType}
                      className="section1-trend-bars-segment"
                      style={{
                        height: `${height}%`,
                        bottom: `${offset}%`,
                        background: `${color}66`,
                        borderColor: `${color}aa`,
                      }}
                    />
                  )
                  offset += height
                  return segment
                })}
              </div>
              <span>{String(year).slice(-2)}</span>
            </div>
          )
        })}
      </div>
      {hoverBreakdown ? (
        <div className="section1-trend-hover-card" style={{ left: `${hoverBreakdown.left}px`, top: `${hoverBreakdown.top}px` }}>
          <div className="section1-trend-hover-card-head">
            <strong>{hoverBreakdown.year}</strong>
            <span>{formatSectionCount(hoverBreakdown.total)} total</span>
          </div>
          <div className="section1-trend-hover-grid">
            {hoverBreakdown.items.map((item) => (
              <div key={`${hoverBreakdown.year}-${item.name}`} className="section1-trend-hover-row">
                <div className="section1-trend-hover-label">{item.name}</div>
                <div className="section1-trend-hover-track">
                  <span
                    className="section1-trend-hover-fill"
                    style={{
                      width: `${Math.max(3, item.share)}%`,
                      background: `${item.color}cc`,
                    }}
                  />
                </div>
                <div className="section1-trend-hover-value">{`${formatSectionCount(item.value)} (${item.share.toFixed(1)}%)`}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}

export function SectionTrendPriceLines({
  history,
  colors,
  className = "section1-trend-lines",
}: {
  history: SectionTrendPoint[]
  colors: Record<string, string>
  className?: string
}) {
  const shellRef = useRef<HTMLDivElement | null>(null)
  const [hoverState, setHoverState] = useState<{ year: number; left: number; top: number } | null>(null)
  const width = 720
  const height = 180
  const padding = 18
  const { years, flatTypes, byYear } = useMemo(() => buildHistoryMatrix(history), [history])
  const prices = history.map((item) => item.medianPrice)
  const maxPrice = Math.max(...prices, 1)
  const xForIndex = (index: number) => padding + (index / Math.max(years.length - 1, 1)) * (width - padding * 2)
  const yForValue = (value: number) => height - padding - (value / maxPrice) * (height - padding * 2)

  const hoverBreakdown = useMemo(() => {
    if (!hoverState) return null
    const items = flatTypes
      .map((flatType) => {
        const point = byYear.get(hoverState.year)?.get(flatType)
        return point
          ? { name: flatType, value: point.medianPrice, color: colors[flatType] ?? "#7f8d9e" }
          : null
      })
      .filter((item): item is { name: string; value: number; color: string } => item !== null)
      .sort((left, right) => right.value - left.value)

    return { ...hoverState, items }
  }, [byYear, colors, flatTypes, hoverState])

  return (
    <div className="section1-trend-shell" ref={shellRef} onMouseLeave={() => setHoverState(null)}>
      <svg className={className} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-hidden="true">
        {hoverBreakdown ? (
          <line
            x1={xForIndex(years.indexOf(hoverBreakdown.year))}
            x2={xForIndex(years.indexOf(hoverBreakdown.year))}
            y1={padding}
            y2={height - padding}
            stroke="rgba(87, 78, 65, 0.22)"
            strokeDasharray="4 4"
            strokeWidth="1.25"
          />
        ) : null}
        {flatTypes.map((flatType) => {
          const points = years
            .map((year, index) => {
              const row = byYear.get(year)?.get(flatType)
              if (!row) return null
              return `${xForIndex(index)},${yForValue(row.medianPrice)}`
            })
            .filter(Boolean)
            .join(" ")
          if (!points) return null
          const color = colors[flatType] ?? "#7f8d9e"
          return (
            <g key={flatType}>
              <polyline fill="none" stroke={color} strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" points={points} />
              {years.map((year, index) => {
                const row = byYear.get(year)?.get(flatType)
                if (!row) return null
                return <circle key={`${flatType}-${year}`} cx={xForIndex(index)} cy={yForValue(row.medianPrice)} r="2.6" fill={color} />
              })}
            </g>
          )
        })}
        {years.map((year, index) => {
          const x = xForIndex(index)
          const previousX = index === 0 ? padding : (xForIndex(index - 1) + x) / 2
          const nextX = index === years.length - 1 ? width - padding : (x + xForIndex(index + 1)) / 2
          return (
            <rect
              key={`hit-${year}`}
              x={previousX}
              y={padding}
              width={Math.max(nextX - previousX, 6)}
              height={height - padding * 2}
              fill="transparent"
              pointerEvents="all"
              onMouseEnter={(event) => {
                const shell = shellRef.current
                if (!shell) return
                const shellRect = shell.getBoundingClientRect()
                const targetRect = event.currentTarget.getBoundingClientRect()
                setHoverState({
                  year,
                  left: Math.min(Math.max(targetRect.left - shellRect.left + targetRect.width * 0.6, 14), Math.max(shellRect.width - 286, 14)),
                  top: 14,
                })
              }}
            />
          )
        })}
      </svg>
      {hoverBreakdown ? (
        <div className="section1-trend-hover-card" style={{ left: `${hoverBreakdown.left}px`, top: `${hoverBreakdown.top}px` }}>
          <div className="section1-trend-hover-card-head">
            <strong>{hoverBreakdown.year}</strong>
            <span>Median prices</span>
          </div>
          <div className="section1-trend-hover-grid">
            {hoverBreakdown.items.map((item) => (
              <div key={`${hoverBreakdown.year}-${item.name}`} className="section1-trend-hover-row section1-trend-hover-row-price">
                <div className="section1-trend-hover-label">{item.name}</div>
                <div className="section1-trend-hover-swatch" style={{ background: item.color }} />
                <div className="section1-trend-hover-value">{formatSectionCurrency(item.value)}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
