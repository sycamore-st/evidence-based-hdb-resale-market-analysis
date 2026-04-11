"use client"

import dynamic from "next/dynamic"
import { useEffect, useMemo, useRef, useState } from "react"

import {
  DashboardPager,
  formatSectionCount,
  formatSectionCurrency,
  SECTION1_CONTROL_LABELS,
  SECTION1_FLAT_COLORS,
  SectionDashboardNav,
} from "@/components/section1/dashboard-shared"
import { SectionTrendPriceLines, SectionTrendStackedBars } from "@/components/section1/dashboard-trend-charts"
import type {
  DashboardThreeCandidate,
  DashboardThreeGeometryFeature,
  DashboardThreeManifest,
  DashboardThreeTownPayload,
} from "@/lib/section1-dashboard3"

const Plot = dynamic(() => import("@/components/charts/plotly-chart"), { ssr: false })

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

function boundsFromPoints(points: Array<{ longitude: number; latitude: number }>) {
  if (points.length === 0) {
    return { minLon: 103.8, maxLon: 103.9, minLat: 1.28, maxLat: 1.36 }
  }

  let minLon = Number.POSITIVE_INFINITY
  let maxLon = Number.NEGATIVE_INFINITY
  let minLat = Number.POSITIVE_INFINITY
  let maxLat = Number.NEGATIVE_INFINITY

  for (const point of points) {
    minLon = Math.min(minLon, point.longitude)
    maxLon = Math.max(maxLon, point.longitude)
    minLat = Math.min(minLat, point.latitude)
    maxLat = Math.max(maxLat, point.latitude)
  }

  return {
    minLon: minLon - 0.002,
    maxLon: maxLon + 0.002,
    minLat: minLat - 0.002,
    maxLat: maxLat + 0.002,
  }
}

function boundsAroundPoint(longitude: number, latitude: number, lonDelta = 0.0045, latDelta = 0.0035) {
  return {
    minLon: longitude - lonDelta,
    maxLon: longitude + lonDelta,
    minLat: latitude - latDelta,
    maxLat: latitude + latDelta,
  }
}

function buildSearchParams(filters: {
  slug: string
  year: number
  budget: number
  flatTypes: string[]
  minFloorArea: number
  maxMrtDistanceKm: number
  minSchoolCount: number
  nearestSchools: string[]
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
  for (const school of filters.nearestSchools) {
    params.append("school", school)
  }
  if (filters.buildingKey) {
    params.set("buildingKey", filters.buildingKey)
  }
  return params
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
          [0.667, "rgba(196, 55, 55, 0.72)"],
          [1, "rgba(196, 55, 55, 0.72)"],
        ],
        marker: {
          line: {
            color: "#9a5f2b",
            width: 0.9,
          },
        },
        showscale: false,
        customdata: locations,
        text: townGeojson.features.map((feature) => {
          const props = geometry.features.find((item) => item.properties["Building Key"] === feature.properties.id)?.properties
          const streetName = props?.["Street Name"] ?? "N/A"
          const postal = props?.["Postal Code"] ?? "N/A"
          const latestYear = props?.["Latest Transaction Year"] ?? "N/A"
          const latestPrice =
            typeof props?.["Latest Transaction Price"] === "number"
              ? formatSectionCurrency(props["Latest Transaction Price"])
              : "N/A"
          return [
            `Block ${feature.properties.block}`,
            `Street: ${streetName}`,
            `Postal code: ${postal}`,
            `Latest transaction year: ${latestYear}`,
            `Latest transaction price: ${latestPrice}`,
          ].join("<br>")
        }),
        hovertemplate: "%{text}<extra></extra>",
      },
      ...[
        {
          poiType: "Bus Stop",
          color: "#d27b61",
          label: "Bus stop",
          glyph: "B",
          size: 11,
          lineColor: "#b25e47",
        },
        {
          poiType: "MRT",
          color: "#5c7695",
          label: "MRT",
          glyph: "M",
          size: 11,
          lineColor: "#47627e",
        },
        {
          poiType: "School",
          color: "#7f9f86",
          label: "School",
          glyph: "S",
          size: 11,
          lineColor: "#5d7e65",
        },
      ]
        .map((group) => {
          const points = nearbyAmenities.filter((amenity) => amenity.poiType === group.poiType)
          if (points.length === 0) return null
          return {
            type: "scattermap",
            mode: "markers+text",
            lon: points.map((point) => point.longitude),
            lat: points.map((point) => point.latitude),
            text: points.map(() => group.glyph),
            textposition: "middle center",
            textfont: {
              color: "#fffdf9",
              family: '"Avenir Next", "Segoe UI", sans-serif',
              size: 7,
            },
            marker: {
              size: group.size,
              color: group.color,
              symbol: "circle",
              opacity: 0.96,
              line: {
                color: group.lineColor,
                width: 1.6,
              },
            },
            customdata: points.map((point) => `${group.label}: ${point.poiName}<br>${formatDistance(point.distanceKm)}`),
            hovertemplate: "%{customdata}<extra></extra>",
            showlegend: false,
          }
        })
        .filter(Boolean),
    ]
  }, [candidates, geometry.features, nearbyAmenities, selectedBuildingKey])

  const layout = useMemo(() => {
    const bounds = selectedBuilding
      ? boundsAroundPoint(selectedBuilding.longitude, selectedBuilding.latitude, 0.0026, 0.002)
      : boundsFromGeometry(geometry.features)
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
      hoverlabel: {
        bgcolor: "rgba(255, 253, 249, 0.94)",
        bordercolor: "rgba(87, 78, 65, 0.16)",
        font: {
          color: "#26231f",
          family: '"Avenir Next", "Segoe UI", sans-serif',
          size: 12,
        },
      },
      margin: { r: 0, t: 0, l: 0, b: 0 },
      height: 540,
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
    }
  }, [geometry.features, nearbyAmenities, selectedBuilding])

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
  const [selectedNearestSchools, setSelectedNearestSchools] = useState<string[]>(initialPayload.filters.nearestSchools)
  const [selectedBuildingKey, setSelectedBuildingKey] = useState<string | null>(initialPayload.selectedBuildingKey)
  const [payload, setPayload] = useState(initialPayload)
  const [loading, setLoading] = useState(false)
  const [flatTypeMenuOpen, setFlatTypeMenuOpen] = useState(false)
  const [schoolMenuOpen, setSchoolMenuOpen] = useState(false)

  const town = manifest.towns.find((item) => item.slug === townSlug) ?? manifest.towns[0]

  useEffect(() => {
    setSelectedFlatTypes(town.filters.flat_types)
    setYear(town.filters.transaction_years[town.filters.transaction_years.length - 1] ?? year)
    setBudget(town.filters.budgets.includes(800000) ? 800000 : (town.filters.budgets[0] ?? budget))
    setMinFloorArea(0)
    setMaxMrtDistanceKm(1.2)
    setMinSchoolCount(0)
    setSelectedNearestSchools([])
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
      nearestSchools: selectedNearestSchools,
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
  }, [townSlug, year, budget, selectedFlatTypes, minFloorArea, maxMrtDistanceKm, minSchoolCount, selectedNearestSchools, selectedBuildingKey])

  const flatTypeSummary =
    selectedFlatTypes.length === town.filters.flat_types.length
      ? "All flat types"
      : selectedFlatTypes.length === 1
        ? selectedFlatTypes[0]
        : `${selectedFlatTypes.length} flat types`
  const schoolSummary =
    selectedNearestSchools.length === 0
      ? "Any nearby school"
      : selectedNearestSchools.length === 1
        ? selectedNearestSchools[0]
        : `${selectedNearestSchools.length} schools`
  const buildingOptions = useMemo(() => {
    if (!payload.selectedBuilding || payload.candidates.some((candidate) => candidate.buildingKey === payload.selectedBuilding?.buildingKey)) {
      return payload.candidates
    }
    return [payload.selectedBuilding, ...payload.candidates]
  }, [payload.candidates, payload.selectedBuilding])

  return (
    <main className="dashboard3-page">
      <header className="dashboard3-header">
        <div>
          <p className="dashboard3-kicker">Section 1 / Interactive Dashboard 3</p>
          <h1>Find Flats by Budget and Location</h1>
          <p>Shortlist HDB buildings by affordability and proximity to MRT, bus stops, schools, and the CBD.</p>
        </div>
        <div className="dashboard3-header-actions">
          <SectionDashboardNav className="dashboard3-header-actions-links" />
        </div>
      </header>

      <section className="dashboard3-layout">
        <aside className="dashboard3-filters">
          <div className="dashboard3-step-label">1. Set your budget and access preferences.</div>

          <label className="dashboard3-control">
            <span className="dashboard1-control-label">
              {SECTION1_CONTROL_LABELS.town}
              <span className="dashboard1-info-trigger" aria-label="Info">
                i
                <span className="dashboard1-info-tooltip">Loads the map and building data for this town.</span>
              </span>
            </span>
            <select value={townSlug} onChange={(event) => setTownSlug(event.target.value)}>
              {manifest.towns.map((item) => (
                <option key={item.slug} value={item.slug}>
                  {item.town}
                </option>
              ))}
            </select>
          </label>

          <div className="dashboard3-control dashboard3-control-multiselect">
            <span className="dashboard1-control-label">
              {SECTION1_CONTROL_LABELS.flatType}
              <span className="dashboard1-info-trigger" aria-label="Info">
                i
                <span className="dashboard1-info-tooltip">Narrows the map and shortlist to these flat types.</span>
              </span>
            </span>
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
            <span className="dashboard1-control-label">
              {SECTION1_CONTROL_LABELS.budget}
              <span className="dashboard1-info-trigger" aria-label="Info">
                i
                <span className="dashboard1-info-tooltip">Only buildings with median price at or below this amount.</span>
              </span>
            </span>
            <select value={budget} onChange={(event) => setBudget(Number(event.target.value))}>
              {town.filters.budgets.map((item) => (
                <option key={item} value={item}>
                  {formatSectionCurrency(item)}
                </option>
              ))}
            </select>
          </label>

          <label className="dashboard3-control">
            <span className="dashboard1-control-label">
              {SECTION1_CONTROL_LABELS.transactionYear}
              <span className="dashboard1-info-trigger" aria-label="Info">
                i
                <span className="dashboard1-info-tooltip">Filters buildings and trends to this year.</span>
              </span>
            </span>
            <select value={year} onChange={(event) => setYear(Number(event.target.value))}>
              {[...town.filters.transaction_years].reverse().map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>

          <label className="dashboard3-control">
            <span className="dashboard1-control-label">
              {SECTION1_CONTROL_LABELS.medianFloorArea}
              <span className="dashboard1-info-trigger" aria-label="Info">
                i
                <span className="dashboard1-info-tooltip">Minimum floor area — excludes smaller units.</span>
              </span>
            </span>
            <select value={minFloorArea} onChange={(event) => setMinFloorArea(Number(event.target.value))}>
              {[0, 50, 70, 90, 110, 130].map((item) => (
                <option key={item} value={item}>
                  {item === 0 ? "Any size" : `${item} sqm or more`}
                </option>
              ))}
            </select>
          </label>

          <label className="dashboard3-control">
            <span className="dashboard1-control-label">
              {SECTION1_CONTROL_LABELS.schoolCountWithin1Km}
              <span className="dashboard1-info-trigger" aria-label="Info">
                i
                <span className="dashboard1-info-tooltip">Minimum number of schools within 1 km of the building.</span>
              </span>
            </span>
            <select value={minSchoolCount} onChange={(event) => setMinSchoolCount(Number(event.target.value))}>
              {[0, 1, 2, 3, 5].map((item) => (
                <option key={item} value={item}>
                  {item === 0 ? "Any count" : `${item}+ schools`}
                </option>
              ))}
            </select>
          </label>

          <div className="dashboard3-control dashboard3-control-multiselect">
            <span className="dashboard1-control-label">
              {SECTION1_CONTROL_LABELS.nearestSchoolWithin1Km}
              <span className="dashboard1-info-trigger" aria-label="Info">
                i
                <span className="dashboard1-info-tooltip">Filter by specific nearby schools.</span>
              </span>
            </span>
            <button type="button" className="dashboard3-multiselect-button" onClick={() => setSchoolMenuOpen((open) => !open)}>
              <strong>{schoolSummary}</strong>
              <span>{schoolMenuOpen ? "Hide" : "Choose"}</span>
            </button>
            {schoolMenuOpen ? (
              <div className="dashboard3-multiselect-menu">
                {payload.availableNearestSchools.map((school) => (
                  <label key={school} className="dashboard3-multiselect-option">
                    <input
                      type="checkbox"
                      checked={selectedNearestSchools.includes(school)}
                      onChange={() =>
                        setSelectedNearestSchools((current) =>
                          current.includes(school)
                            ? current.filter((item) => item !== school)
                            : [...current, school].sort((left, right) => left.localeCompare(right)),
                        )
                      }
                    />
                    <span>{school}</span>
                  </label>
                ))}
              </div>
            ) : null}
          </div>

          <label className="dashboard3-control">
            <span className="dashboard1-control-label">
              {SECTION1_CONTROL_LABELS.nearestMrtDistance}
              <span className="dashboard1-info-trigger" aria-label="Info">
                i
                <span className="dashboard1-info-tooltip">Maximum walking distance to the nearest MRT station.</span>
              </span>
            </span>
            <select value={maxMrtDistanceKm} onChange={(event) => setMaxMrtDistanceKm(Number(event.target.value))}>
              {[0.4, 0.6, 0.8, 1.2, 2].map((item) => (
                <option key={item} value={item}>
                  Up to {item.toFixed(1)} km
                </option>
              ))}
            </select>
          </label>

          <div className="dashboard3-summary-card">
            <span className="dashboard1-control-label">
              Current shortlist
              <span className="dashboard1-info-trigger" aria-label="Info">
                i
                <span className="dashboard1-info-tooltip">Buildings matching all your filters above.</span>
              </span>
            </span>
            <strong>{formatSectionCount(payload.summary.shortlistCount)}</strong>
            <small>{formatSectionCount(payload.summary.buildingRowsScanned)} matching building-flat rows after filters.</small>
          </div>
        </aside>

        <section className="dashboard3-selector-card">
          <div className="dashboard3-step-label">2. Pick a building from the map or dropdown to see its location, nearby amenities, and transaction history.</div>
          <div className="dashboard3-selected-building">
            <span>Selected building</span>
            <h3>
              {payload.selectedBuilding ? `Block ${payload.selectedBuilding.block} / ${payload.selectedBuilding.bestFlatType}` : "No shortlist match"}
            </h3>
          </div>
          <label className="dashboard3-control dashboard3-building-picker">
            <span>{SECTION1_CONTROL_LABELS.selectedBuilding}</span>
            <select
              value={payload.selectedBuildingKey ?? ""}
              onChange={(event) => setSelectedBuildingKey(event.target.value || null)}
            >
              {buildingOptions.map((candidate) => (
                <option key={candidate.buildingKey} value={candidate.buildingKey}>
                  {`Block ${candidate.block} / ${candidate.bestFlatType} / ${formatSectionCurrency(candidate.latestTransactionPrice ?? candidate.medianPrice)}`}
                </option>
              ))}
            </select>
            <small>Select from the map or this dropdown.</small>
          </label>
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
              <span><i className="dashboard3-legend-chip dashboard3-legend-bus-stop">B</i>Bus stop</span>
              <span><i className="dashboard3-legend-chip dashboard3-legend-mrt">M</i>MRT</span>
              <span><i className="dashboard3-legend-chip dashboard3-legend-school">S</i>School</span>
              <span><i className="dashboard3-legend-chip dashboard3-legend-candidate" />Meets criteria</span>
              <span><i className="dashboard3-legend-chip dashboard3-legend-selected" />Selected building</span>
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
          </div>
        </section>

        <section className="dashboard3-trends-card">
          <div className="dashboard3-trends-wrap">
            <div className="dashboard3-trend-panel">
              <div className="dashboard1-chart-header">
                <h3>Transactions over time</h3>
                <p>How many deals closed each year at this building, broken down by flat type.</p>
              </div>
              <SectionTrendStackedBars history={payload.history} colors={SECTION1_FLAT_COLORS} className="dashboard3-bars" />
            </div>
            <div className="dashboard3-trend-panel">
              <div className="dashboard1-chart-header">
                <h3>Median price over time</h3>
                <p>The middle-of-the-pack resale price each year. Compare lines across flat types.</p>
              </div>
              <SectionTrendPriceLines history={payload.history} colors={SECTION1_FLAT_COLORS} className="dashboard3-lines" />
            </div>
          </div>
          <div className="dashboard3-flat-legend">
            {Array.from(new Set(payload.history.map((item) => item.flatType))).map((flatType) => (
              <span key={flatType}>
                <i style={{ background: `${SECTION1_FLAT_COLORS[flatType] ?? "#b79f96"}88`, borderColor: `${SECTION1_FLAT_COLORS[flatType] ?? "#b79f96"}cc` }} />
                {flatType}
              </span>
            ))}
          </div>
        </section>
      </section>

      {loading ? (
        <div className="dashboard3-loading-overlay">
          <div className="dashboard3-loading">
            <div className="dashboard3-loading-dots">
              <span className="dashboard3-loading-dot" />
              <span className="dashboard3-loading-dot" />
              <span className="dashboard3-loading-dot" />
            </div>
            <p>Refreshing shortlist…</p>
          </div>
        </div>
      ) : null}

      <DashboardPager current="/section1/dashboard-3" />
    </main>
  )
}
