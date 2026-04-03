"use client"

import dynamic from "next/dynamic"
import Link from "next/link"
import { useEffect, useMemo, useState } from "react"

import type {
  DashboardThreeCandidate,
  DashboardThreeGeometryFeature,
  DashboardThreeHistoryPoint,
  DashboardThreeManifest,
  DashboardThreeTownPayload,
} from "@/lib/section1-dashboard3"

const Plot = dynamic(() => import("@/components/charts/plotly-chart"), { ssr: false })

const FLAT_TYPE_COLORS: Record<string, string> = {
  "1 ROOM": "#b79f96",
  "2 ROOM": "#b79f96",
  "3 ROOM": "#b79f96",
  "4 ROOM": "#d1bf9f",
  "5 ROOM": "#a8b6aa",
  EXECUTIVE: "#7f8d9e",
  "MULTI-GENERATION": "#7f8d9e",
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-SG", {
    style: "currency",
    currency: "SGD",
    maximumFractionDigits: 0,
  }).format(value)
}

function formatCount(value: number): string {
  return new Intl.NumberFormat("en-SG").format(value)
}

function formatDistance(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "N/A"
  }
  return `${value.toFixed(2)} km`
}

function flattenCoordinates(coordinates: unknown): number[][][] {
  if (!Array.isArray(coordinates)) return []
  if (coordinates.length === 0) return []
  const first = coordinates[0]
  if (Array.isArray(first) && Array.isArray(first[0]) && typeof first[0][0] === "number") {
    return coordinates as number[][][]
  }
  let rings: number[][][] = []
  for (const item of coordinates) {
    rings = rings.concat(flattenCoordinates(item))
  }
  return rings
}

function boundsFromGeometry(features: DashboardThreeGeometryFeature[]) {
  let minLon = Number.POSITIVE_INFINITY
  let maxLon = Number.NEGATIVE_INFINITY
  let minLat = Number.POSITIVE_INFINITY
  let maxLat = Number.NEGATIVE_INFINITY

  for (const feature of features) {
    for (const ring of flattenCoordinates(feature.geometry.coordinates)) {
      for (const point of ring) {
        const [lon, lat] = point
        minLon = Math.min(minLon, lon)
        maxLon = Math.max(maxLon, lon)
        minLat = Math.min(minLat, lat)
        maxLat = Math.max(maxLat, lat)
      }
    }
  }

  if (!Number.isFinite(minLon)) {
    return { minLon: 103.8, maxLon: 103.9, minLat: 1.28, maxLat: 1.36 }
  }
  return { minLon, maxLon, minLat, maxLat }
}

function estimateMapZoom(bounds: { minLon: number; maxLon: number; minLat: number; maxLat: number }) {
  const lonSpan = Math.max(bounds.maxLon - bounds.minLon, 0.0025)
  const latSpan = Math.max(bounds.maxLat - bounds.minLat, 0.0025)
  const dominantSpan = Math.max(lonSpan * 1.45, latSpan * 1.15)
  const zoom = Math.log2(360 / dominantSpan)
  return Math.max(11, Math.min(19, zoom))
}

function buildSearchParams(filters: {
  slug: string
  year: number
  budget: number
  flatTypes: string[]
  minFloorArea: number
  maxMrtDistanceKm: number
  minSchoolCount: number
  buildingKey: string | null
}) {
  const params = new URLSearchParams()
  params.set("slug", filters.slug)
  params.set("year", String(filters.year))
  params.set("budget", String(filters.budget))
  params.set("minFloorArea", String(filters.minFloorArea))
  params.set("maxMrtDistanceKm", String(filters.maxMrtDistanceKm))
  params.set("minSchoolCount", String(filters.minSchoolCount))
  for (const flatType of filters.flatTypes) {
    params.append("flatType", flatType)
  }
  if (filters.buildingKey) {
    params.set("buildingKey", filters.buildingKey)
  }
  return params
}

function TransactionBars({ history }: { history: DashboardThreeHistoryPoint[] }) {
  const years = Array.from(new Set(history.map((item) => item.year))).sort((left, right) => left - right)
  const flatTypes = Array.from(new Set(history.map((item) => item.flatType))).sort((left, right) => left.localeCompare(right))
  const totals = years.map((year) =>
    flatTypes.map((flatType) => history.find((item) => item.year === year && item.flatType === flatType)?.transactions ?? 0),
  )
  const maxTotal = Math.max(...totals.map((values) => values.reduce((sum, value) => sum + value, 0)), 1)

  return (
    <div className="dashboard3-bars">
      {years.map((year, index) => {
        let offset = 0
        const yearValues = totals[index]
        const total = yearValues.reduce((sum, value) => sum + value, 0)
        return (
          <div key={year} className="dashboard3-bars-year">
            <div className="dashboard3-bars-stack">
              {flatTypes.map((flatType, flatIndex) => {
                const value = yearValues[flatIndex]
                const height = total > 0 ? (value / maxTotal) * 100 : 0
                const segment = (
                  <span
                    key={flatType}
                    className="dashboard3-bars-segment"
                    style={{
                      height: `${height}%`,
                      bottom: `${offset}%`,
                      background: `${FLAT_TYPE_COLORS[flatType] ?? "#b79f96"}66`,
                      borderColor: `${FLAT_TYPE_COLORS[flatType] ?? "#b79f96"}aa`,
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
  )
}

function PriceLines({ history }: { history: DashboardThreeHistoryPoint[] }) {
  const width = 720
  const height = 180
  const padding = 18
  const years = Array.from(new Set(history.map((item) => item.year))).sort((left, right) => left - right)
  const flatTypes = Array.from(new Set(history.map((item) => item.flatType))).sort((left, right) => left.localeCompare(right))
  const prices = history.map((item) => item.medianPrice)
  const maxPrice = Math.max(...prices, 1)
  const xForIndex = (index: number) => padding + (index / Math.max(years.length - 1, 1)) * (width - padding * 2)
  const yForValue = (value: number) => height - padding - (value / maxPrice) * (height - padding * 2)

  return (
    <svg className="dashboard3-lines" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-hidden="true">
      {[0, 0.33, 0.66, 1].map((stop) => (
        <line
          key={stop}
          x1={padding}
          x2={width - padding}
          y1={height - padding - stop * (height - padding * 2)}
          y2={height - padding - stop * (height - padding * 2)}
          stroke="rgba(87, 78, 65, 0.12)"
          strokeWidth="1"
        />
      ))}
      {flatTypes.map((flatType) => {
        const points = years
          .map((year, index) => {
            const row = history.find((item) => item.year === year && item.flatType === flatType)
            if (!row) return null
            return `${xForIndex(index)},${yForValue(row.medianPrice)}`
          })
          .filter(Boolean)
          .join(" ")
        if (!points) return null
        return (
          <g key={flatType}>
            <polyline
              fill="none"
              stroke={FLAT_TYPE_COLORS[flatType] ?? "#7f8d9e"}
              strokeWidth="3"
              strokeLinejoin="round"
              strokeLinecap="round"
              points={points}
            />
            {years.map((year, index) => {
              const row = history.find((item) => item.year === year && item.flatType === flatType)
              if (!row) return null
              return (
                <circle
                  key={`${flatType}-${year}`}
                  cx={xForIndex(index)}
                  cy={yForValue(row.medianPrice)}
                  r="3.5"
                  fill={FLAT_TYPE_COLORS[flatType] ?? "#7f8d9e"}
                />
              )
            })}
          </g>
        )
      })}
    </svg>
  )
}

function SelectorMap({
  geometry,
  candidates,
  selectedBuildingKey,
  selectedBuilding,
  nearbyAmenities,
  onSelect,
}: {
  geometry: DashboardThreeTownPayload["geometry"]
  candidates: DashboardThreeCandidate[]
  selectedBuildingKey: string | null
  selectedBuilding: DashboardThreeCandidate | null
  nearbyAmenities: DashboardThreeTownPayload["nearbyAmenities"]
  onSelect: (buildingKey: string) => void
}) {
  const data = useMemo(() => {
    const eligibleKeys = new Set(candidates.map((candidate) => candidate.buildingKey))
    const townGeojson = {
      type: "FeatureCollection",
      features: geometry.features.map((feature) => ({
        type: "Feature" as const,
        properties: {
          id: feature.properties["Building Key"],
          block: feature.properties.Block,
        },
        geometry: feature.geometry,
      })),
    }
    const locations = townGeojson.features.map((feature) => feature.properties.id)
    const zValues = locations.map((location) => {
      if (location === selectedBuildingKey && eligibleKeys.has(location)) return 2
      if (eligibleKeys.has(location)) return 1
      return 0
    })

    return [
      {
        type: "choroplethmap",
        geojson: townGeojson,
        locations,
        z: zValues,
        zmin: 0,
        zmax: 2,
        featureidkey: "properties.id",
        colorscale: [
          [0, "rgba(255, 255, 255, 0)"],
          [0.333, "rgba(255, 255, 255, 0)"],
          [0.334, "rgba(220, 145, 71, 0.28)"],
          [0.666, "rgba(220, 145, 71, 0.28)"],
          [0.667, "rgba(154, 95, 43, 0.88)"],
          [1, "rgba(154, 95, 43, 0.88)"],
        ],
        marker: {
          line: {
            color: "#9a5f2b",
            width: 0.9,
          },
        },
        showscale: false,
        customdata: locations,
        text: townGeojson.features.map((feature) => `Block ${feature.properties.block}`),
        hovertemplate: "%{text}<extra></extra>",
      },
    ]
  }, [candidates, geometry.features, selectedBuildingKey])

  const layout = useMemo(() => {
    const bounds = boundsFromGeometry(geometry.features)
    const center = {
      lon: (bounds.minLon + bounds.maxLon) / 2,
      lat: (bounds.minLat + bounds.maxLat) / 2,
    }
    return {
      map: {
        style: "carto-positron",
        center,
        zoom: estimateMapZoom(bounds),
      },
      margin: { r: 0, t: 0, l: 0, b: 0 },
      height: 540,
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
    }
  }, [geometry.features])

  return (
    <Plot
      className="dashboard3-map"
      useResizeHandler
      style={{ width: "100%", height: "34rem" }}
      data={data}
      layout={layout}
      onClick={(event) => {
        const points = (event as { points?: Array<{ customdata?: string; location?: string }> }).points
        const point = points?.[0]
        const buildingKey = point?.customdata ?? point?.location
        if (typeof buildingKey === "string" && buildingKey.length > 0) {
          onSelect(buildingKey)
        }
      }}
      config={{
        displayModeBar: true,
        displaylogo: false,
        responsive: true,
        scrollZoom: true,
        modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d", "toggleSpikelines"],
      }}
    />
  )
}

export function DashboardThreeExplorer({
  manifest,
  initialPayload,
}: {
  manifest: DashboardThreeManifest
  initialPayload: DashboardThreeTownPayload
}) {
  const [townSlug, setTownSlug] = useState(initialPayload.town.slug)
  const [year, setYear] = useState(initialPayload.filters.year)
  const [budget, setBudget] = useState(initialPayload.filters.budget)
  const [selectedFlatTypes, setSelectedFlatTypes] = useState<string[]>(initialPayload.filters.flatTypes)
  const [minFloorArea, setMinFloorArea] = useState(initialPayload.filters.minFloorArea)
  const [maxMrtDistanceKm, setMaxMrtDistanceKm] = useState(initialPayload.filters.maxMrtDistanceKm)
  const [minSchoolCount, setMinSchoolCount] = useState(initialPayload.filters.minSchoolCount)
  const [selectedBuildingKey, setSelectedBuildingKey] = useState<string | null>(initialPayload.selectedBuildingKey)
  const [payload, setPayload] = useState(initialPayload)
  const [loading, setLoading] = useState(false)
  const [flatTypeMenuOpen, setFlatTypeMenuOpen] = useState(false)

  const town = manifest.towns.find((item) => item.slug === townSlug) ?? manifest.towns[0]

  useEffect(() => {
    setSelectedFlatTypes(town.filters.flat_types)
    setYear(town.filters.transaction_years[town.filters.transaction_years.length - 1] ?? year)
    setBudget(town.filters.budgets.includes(800000) ? 800000 : (town.filters.budgets[0] ?? budget))
    setMinFloorArea(0)
    setMaxMrtDistanceKm(1.2)
    setMinSchoolCount(0)
    setSelectedBuildingKey(null)
  }, [townSlug])

  useEffect(() => {
    const controller = new AbortController()
    const params = buildSearchParams({
      slug: townSlug,
      year,
      budget,
      flatTypes: selectedFlatTypes,
      minFloorArea,
      maxMrtDistanceKm,
      minSchoolCount,
      buildingKey: selectedBuildingKey,
    })

    setLoading(true)
    fetch(`/api/section1/dashboard-3?${params.toString()}`, { signal: controller.signal })
      .then((response) => response.json() as Promise<DashboardThreeTownPayload>)
      .then((nextPayload) => {
        setPayload(nextPayload)
        setSelectedBuildingKey(nextPayload.selectedBuildingKey)
      })
      .catch((error: unknown) => {
        if ((error as { name?: string }).name !== "AbortError") {
          console.error(error)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      })

    return () => controller.abort()
  }, [townSlug, year, budget, selectedFlatTypes, minFloorArea, maxMrtDistanceKm, minSchoolCount, selectedBuildingKey])

  const flatTypeSummary =
    selectedFlatTypes.length === town.filters.flat_types.length
      ? "All flat types"
      : selectedFlatTypes.length === 1
        ? selectedFlatTypes[0]
        : `${selectedFlatTypes.length} flat types`

  return (
    <main className="dashboard3-page">
      <header className="dashboard3-header">
        <div>
          <p className="dashboard3-kicker">Section 1 / Interactive Dashboard 3</p>
          <h1>Find Flats by Budget and Location</h1>
          <p>Shortlist HDB buildings by affordability and proximity to MRT, bus stops, schools, and the CBD.</p>
        </div>
        <div className="dashboard3-header-actions">
          <Link href="/section1/dashboard-2" className="dashboard3-link">
            Back to Dashboard 2
          </Link>
          <Link href="/" className="dashboard3-link">
            Back to index
          </Link>
        </div>
      </header>

      <section className="dashboard3-layout">
        <aside className="dashboard3-filters">
          <div className="dashboard3-step-label">1. Set your budget and access preferences.</div>

          <label className="dashboard3-control">
            <span>Town</span>
            <select value={townSlug} onChange={(event) => setTownSlug(event.target.value)}>
              {manifest.towns.map((item) => (
                <option key={item.slug} value={item.slug}>
                  {item.town}
                </option>
              ))}
            </select>
          </label>

          <div className="dashboard3-control dashboard3-control-multiselect">
            <span>Flat Type</span>
            <button type="button" className="dashboard3-multiselect-button" onClick={() => setFlatTypeMenuOpen((open) => !open)}>
              <strong>{flatTypeSummary}</strong>
              <span>{flatTypeMenuOpen ? "Hide" : "Choose"}</span>
            </button>
            {flatTypeMenuOpen ? (
              <div className="dashboard3-multiselect-menu">
                {town.filters.flat_types.map((flatType) => (
                  <label key={flatType} className="dashboard3-multiselect-option">
                    <input
                      type="checkbox"
                      checked={selectedFlatTypes.includes(flatType)}
                      onChange={() =>
                        setSelectedFlatTypes((current) => {
                          const next = current.includes(flatType)
                            ? current.filter((item) => item !== flatType)
                            : [...current, flatType]
                          return next.length === 0 ? [...town.filters.flat_types] : next.sort((left, right) => left.localeCompare(right))
                        })
                      }
                    />
                    <span>{flatType}</span>
                  </label>
                ))}
              </div>
            ) : null}
          </div>

          <label className="dashboard3-control">
            <span>Budget</span>
            <select value={budget} onChange={(event) => setBudget(Number(event.target.value))}>
              {town.filters.budgets.map((item) => (
                <option key={item} value={item}>
                  {formatCurrency(item)}
                </option>
              ))}
            </select>
          </label>

          <label className="dashboard3-control">
            <span>Transaction year</span>
            <select value={year} onChange={(event) => setYear(Number(event.target.value))}>
              {[...town.filters.transaction_years].reverse().map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>

          <label className="dashboard3-control">
            <span>Median floor area</span>
            <select value={minFloorArea} onChange={(event) => setMinFloorArea(Number(event.target.value))}>
              {[0, 50, 70, 90, 110, 130].map((item) => (
                <option key={item} value={item}>
                  {item === 0 ? "Any size" : `${item} sqm or more`}
                </option>
              ))}
            </select>
          </label>

          <label className="dashboard3-control">
            <span>School count within 1km</span>
            <select value={minSchoolCount} onChange={(event) => setMinSchoolCount(Number(event.target.value))}>
              {[0, 1, 2, 3, 5].map((item) => (
                <option key={item} value={item}>
                  {item === 0 ? "Any count" : `${item}+ schools`}
                </option>
              ))}
            </select>
          </label>

          <label className="dashboard3-control">
            <span>Nearest MRT distance</span>
            <select value={maxMrtDistanceKm} onChange={(event) => setMaxMrtDistanceKm(Number(event.target.value))}>
              {[0.4, 0.6, 0.8, 1.2, 2].map((item) => (
                <option key={item} value={item}>
                  Up to {item.toFixed(1)} km
                </option>
              ))}
            </select>
          </label>

          <div className="dashboard3-summary-card">
            <span>Current shortlist</span>
            <strong>{formatCount(payload.summary.shortlistCount)}</strong>
            <small>{formatCount(payload.summary.buildingRowsScanned)} matching building-flat rows after filters.</small>
          </div>
        </aside>

        <section className="dashboard3-selector-card">
          <div className="dashboard3-panel-header">
            <span>2. Select an HDB building</span>
            <strong>{payload.selectedBuilding ? `${payload.selectedBuilding.block} / ${payload.selectedBuilding.bestFlatType}` : "No shortlist match"}</strong>
          </div>
          {payload.selectedBuilding ? (
            <div className="dashboard3-map-label">
              Selected building: Block {payload.selectedBuilding.block} / {payload.selectedBuilding.bestFlatType}
            </div>
          ) : null}
          <SelectorMap
            geometry={payload.geometry}
            candidates={payload.candidates}
            selectedBuildingKey={payload.selectedBuildingKey}
            selectedBuilding={payload.selectedBuilding}
            nearbyAmenities={payload.nearbyAmenities}
            onSelect={setSelectedBuildingKey}
          />
          <div className="dashboard3-map-footer">
            <div className="dashboard3-poi-legend">
              <span>Bus Stop: +</span>
              <span>MRT: x</span>
              <span>School: o</span>
              <span>Selected building: square</span>
            </div>
            {payload.selectedBuilding ? (
              <div className="dashboard3-building-meta dashboard3-building-meta-inline">
                <div>
                  <span>Nearest MRT</span>
                  <strong>{payload.selectedBuilding.nearestMrtName ?? "N/A"}</strong>
                  <small>{formatDistance(payload.selectedBuilding.nearestMrtDistanceKm)}</small>
                </div>
                <div>
                  <span>Nearest school</span>
                  <strong>{payload.selectedBuilding.nearestSchool ?? "N/A"}</strong>
                  <small>{formatDistance(payload.selectedBuilding.nearestSchoolDistanceKm)}</small>
                </div>
                <div>
                  <span>Distance to CBD</span>
                  <strong>{formatDistance(payload.selectedBuilding.distanceToCbdKm)}</strong>
                  <small>{payload.selectedBuilding.schoolCountWithin1Km ?? 0} schools within 1km</small>
                </div>
              </div>
            ) : null}
            <div className="dashboard3-shortlist">
              {payload.candidates.slice(0, 8).map((candidate) => (
                <button
                  key={candidate.buildingKey}
                  type="button"
                  className={`dashboard3-shortlist-item ${payload.selectedBuildingKey === candidate.buildingKey ? "dashboard3-shortlist-item-active" : ""}`}
                  onClick={() => setSelectedBuildingKey(candidate.buildingKey)}
                >
                  <strong>
                    Block {candidate.block} / {candidate.bestFlatType}
                  </strong>
                  <span>
                    {candidate.medianFloorArea.toFixed(0)} sqm • {formatCurrency(candidate.medianPrice)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="dashboard3-trends-card">
          <div className="dashboard3-panel-header">
            <span>3. Compare transaction volume and median price trends below.</span>
            <strong>{payload.selectedBuilding ? `Block ${payload.selectedBuilding.block}` : "No selected building"}</strong>
          </div>
          <div className="dashboard3-trends-wrap">
            <div className="dashboard3-trend-panel">
              <h2>Transactions over time</h2>
              <TransactionBars history={payload.history} />
            </div>
            <div className="dashboard3-trend-panel">
              <h2>Median price over time</h2>
              <PriceLines history={payload.history} />
            </div>
          </div>
          <div className="dashboard3-flat-legend">
            {Array.from(new Set(payload.history.map((item) => item.flatType))).map((flatType) => (
              <span key={flatType}>
                <i style={{ background: `${FLAT_TYPE_COLORS[flatType] ?? "#b79f96"}88`, borderColor: `${FLAT_TYPE_COLORS[flatType] ?? "#b79f96"}cc` }} />
                {flatType}
              </span>
            ))}
          </div>
        </section>
      </section>

      {loading ? <div className="dashboard3-loading">Refreshing shortlist…</div> : null}
    </main>
  )
}
