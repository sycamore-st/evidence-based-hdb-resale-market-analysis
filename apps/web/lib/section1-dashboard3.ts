import { readFileSync } from "node:fs"
import path from "node:path"

export interface DashboardThreeManifestTown {
  town: string
  slug: string
  counts: {
    building_rows: number
    location_rows: number
    poi_point_rows: number
    poi_summary_rows: number
    geometry_features: number
  }
  filters: {
    transaction_years: number[]
    budgets: number[]
    flat_types: string[]
  }
  files: {
    summary: string
    buildings: string
    location: string
    poi_points: string
    poi_summary: string
    geometry: string
  }
}

export interface DashboardThreeManifest {
  dataset_version: string
  generated_at: string
  artifact_root: string
  filters: {
    towns: string[]
    transaction_years: number[]
    budgets: number[]
    flat_types: string[]
  }
  towns: DashboardThreeManifestTown[]
}

export interface DashboardThreeBuildingRow {
  transaction_year: number
  town: string
  block: string
  flat_type: string
  building_key: string
  postal_code: number | null
  building_latitude: number
  building_longitude: number
  transactions: number
  median_price: number
  median_floor_area: number
  median_price_per_sqm: number
  median_flat_age: number
  budget: number
  budget_slack: number
  nearest_mrt_name: string | null
  nearest_mrt_distance_km: number | null
  nearest_bus_stop: string | number | null
  nearest_bus_stop_distance_km: number | null
  bus_stop_count_within_1km: number | null
  nearest_school: string | null
  nearest_school_distance_km: number | null
  school_count_within_1km: number | null
  distance_to_cbd_km: number | null
  building_match_status: string | null
  has_transaction_data: string | null
  has_building_geometry: string | null
  town_shape_key: string | null
}

export interface DashboardThreePoiPoint {
  town: string
  poi_type: string
  poi_name: string
  poi_latitude: number
  poi_longitude: number
  distance_to_town_km: number
}

export interface DashboardThreeGeometryFeature {
  type: "Feature"
  properties: {
    "Building Key": string
    Block: string
    "Postal Code": string | null
    Town: string
    "Building Match Status": string | null
    "Building Latitude": number
    "Building Longitude": number
  }
  geometry: {
    type: string
    coordinates: unknown[]
  }
}

export interface DashboardThreeCandidate {
  buildingKey: string
  block: string
  postalCode: string | null
  latitude: number
  longitude: number
  flatTypes: string[]
  bestFlatType: string
  medianPrice: number
  medianFloorArea: number
  medianPricePerSqm: number
  medianFlatAge: number
  transactions: number
  budgetSlack: number
  nearestMrtName: string | null
  nearestMrtDistanceKm: number | null
  nearestBusStop: string | null
  nearestBusStopDistanceKm: number | null
  schoolCountWithin1Km: number | null
  nearestSchool: string | null
  nearestSchoolDistanceKm: number | null
  distanceToCbdKm: number | null
  score: number
}

export interface DashboardThreeHistoryPoint {
  year: number
  flatType: string
  transactions: number
  medianPrice: number
}

export interface DashboardThreeNearbyAmenity {
  poiType: string
  poiName: string
  latitude: number
  longitude: number
  distanceKm: number
}

export interface DashboardThreeTownPayload {
  town: DashboardThreeManifestTown
  filters: {
    year: number
    budget: number
    flatTypes: string[]
    minFloorArea: number
    maxMrtDistanceKm: number
    minSchoolCount: number
  }
  summary: {
    shortlistCount: number
    buildingRowsScanned: number
    priceRange: [number, number] | null
    floorAreaRange: [number, number] | null
  }
  candidates: DashboardThreeCandidate[]
  selectedBuildingKey: string | null
  selectedBuilding: DashboardThreeCandidate | null
  history: DashboardThreeHistoryPoint[]
  nearbyAmenities: DashboardThreeNearbyAmenity[]
  geometry: {
    type: "FeatureCollection"
    features: DashboardThreeGeometryFeature[]
  }
}

export interface DashboardThreeQuery {
  slug: string
  year: number
  budget: number
  flatTypes: string[]
  minFloorArea: number
  maxMrtDistanceKm: number
  minSchoolCount: number
  buildingKey?: string | null
}

interface RawTownBundle {
  town: DashboardThreeManifestTown
  buildings: DashboardThreeBuildingRow[]
  poiPoints: DashboardThreePoiPoint[]
  geometry: {
    type: "FeatureCollection"
    features: DashboardThreeGeometryFeature[]
  }
}

const ROOT = path.resolve(process.cwd(), "../..")
const DASHBOARD3_ROOT = path.join(ROOT, "artifacts/web/overview/dashboard3")
const MANIFEST_PATH = path.join(DASHBOARD3_ROOT, "manifest.json")

const manifestCache = { value: null as DashboardThreeManifest | null }
const townBundleCache = new Map<string, RawTownBundle>()

function readJson<T>(filePath: string): T {
  return JSON.parse(readFileSync(filePath, "utf8")) as T
}

function normalizeNumber(value: number | null | undefined, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback
}

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const radius = 6371
  const toRadians = (value: number) => (value * Math.PI) / 180
  const dLat = toRadians(lat2 - lat1)
  const dLon = toRadians(lon2 - lon1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) * Math.sin(dLon / 2) ** 2
  return 2 * radius * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

function candidateScore(row: DashboardThreeBuildingRow): number {
  return (
    normalizeNumber(row.median_floor_area, 0) * 1.8 +
    normalizeNumber(row.budget_slack, 0) / 15000 +
    normalizeNumber(row.school_count_within_1km, 0) * 4 -
    normalizeNumber(row.nearest_mrt_distance_km, 1.5) * 25 -
    normalizeNumber(row.distance_to_cbd_km, 12) * 0.55
  )
}

function chooseRepresentativeRow(current: DashboardThreeBuildingRow, next: DashboardThreeBuildingRow): DashboardThreeBuildingRow {
  if (next.median_floor_area !== current.median_floor_area) {
    return next.median_floor_area > current.median_floor_area ? next : current
  }
  if (next.budget_slack !== current.budget_slack) {
    return next.budget_slack > current.budget_slack ? next : current
  }
  if ((next.nearest_mrt_distance_km ?? Number.POSITIVE_INFINITY) !== (current.nearest_mrt_distance_km ?? Number.POSITIVE_INFINITY)) {
    return (next.nearest_mrt_distance_km ?? Number.POSITIVE_INFINITY) < (current.nearest_mrt_distance_km ?? Number.POSITIVE_INFINITY)
      ? next
      : current
  }
  return next.transactions > current.transactions ? next : current
}

function sortCandidates(left: DashboardThreeCandidate, right: DashboardThreeCandidate): number {
  return (
    right.score - left.score ||
    right.medianFloorArea - left.medianFloorArea ||
    right.budgetSlack - left.budgetSlack ||
    (left.nearestMrtDistanceKm ?? Number.POSITIVE_INFINITY) - (right.nearestMrtDistanceKm ?? Number.POSITIVE_INFINITY) ||
    left.block.localeCompare(right.block)
  )
}

export function loadDashboardThreeManifest(): DashboardThreeManifest {
  if (!manifestCache.value) {
    manifestCache.value = readJson<DashboardThreeManifest>(MANIFEST_PATH)
  }
  return manifestCache.value
}

function loadRawTownBundle(slug: string): RawTownBundle {
  const cached = townBundleCache.get(slug)
  if (cached) {
    return cached
  }

  const manifest = loadDashboardThreeManifest()
  const town = manifest.towns.find((item) => item.slug === slug)
  if (!town) {
    throw new Error(`Unknown Dashboard 3 town slug: ${slug}`)
  }

  const bundle: RawTownBundle = {
    town,
    buildings: readJson<DashboardThreeBuildingRow[]>(path.join(DASHBOARD3_ROOT, town.files.buildings)),
    poiPoints: readJson<DashboardThreePoiPoint[]>(path.join(DASHBOARD3_ROOT, town.files.poi_points)),
    geometry: readJson<{ type: "FeatureCollection"; features: DashboardThreeGeometryFeature[] }>(
      path.join(DASHBOARD3_ROOT, town.files.geometry),
    ),
  }
  townBundleCache.set(slug, bundle)
  return bundle
}

export function defaultDashboardThreeQuery(): DashboardThreeQuery {
  const manifest = loadDashboardThreeManifest()
  const defaultTown =
    manifest.towns.find((town) => town.slug === "bedok") ??
    manifest.towns[0]

  return {
    slug: defaultTown.slug,
    year: defaultTown.filters.transaction_years[defaultTown.filters.transaction_years.length - 1] ?? 2026,
    budget: defaultTown.filters.budgets.includes(800000) ? 800000 : (defaultTown.filters.budgets[0] ?? 800000),
    flatTypes: [...defaultTown.filters.flat_types],
    minFloorArea: 0,
    maxMrtDistanceKm: 1.2,
    minSchoolCount: 0,
    buildingKey: null,
  }
}

export function buildDashboardThreeTownPayload(query: DashboardThreeQuery): DashboardThreeTownPayload {
  const bundle = loadRawTownBundle(query.slug)
  const activeFlatTypes = query.flatTypes.length > 0 ? query.flatTypes : bundle.town.filters.flat_types
  const filteredRows = bundle.buildings.filter((row) => {
    if (row.transaction_year !== query.year) return false
    if (row.budget !== query.budget) return false
    if (!activeFlatTypes.includes(row.flat_type)) return false
    if (row.median_floor_area < query.minFloorArea) return false
    if ((row.nearest_mrt_distance_km ?? Number.POSITIVE_INFINITY) > query.maxMrtDistanceKm) return false
    if ((row.school_count_within_1km ?? 0) < query.minSchoolCount) return false
    if (row.building_match_status !== "matched_geometry") return false
    return row.has_building_geometry === "Yes"
  })

  const grouped = new Map<
    string,
    {
      representative: DashboardThreeBuildingRow
      flatTypes: Set<string>
    }
  >()

  for (const row of filteredRows) {
    const existing = grouped.get(row.building_key)
    if (!existing) {
      grouped.set(row.building_key, {
        representative: row,
        flatTypes: new Set([row.flat_type]),
      })
      continue
    }
    existing.representative = chooseRepresentativeRow(existing.representative, row)
    existing.flatTypes.add(row.flat_type)
  }

  const allCandidates = Array.from(grouped.entries())
    .map(([buildingKey, value]) => {
      const row = value.representative
      return {
        buildingKey,
        block: String(row.block),
        postalCode: row.postal_code != null ? String(row.postal_code) : null,
        latitude: row.building_latitude,
        longitude: row.building_longitude,
        flatTypes: Array.from(value.flatTypes).sort((left, right) => left.localeCompare(right)),
        bestFlatType: row.flat_type,
        medianPrice: row.median_price,
        medianFloorArea: row.median_floor_area,
        medianPricePerSqm: row.median_price_per_sqm,
        medianFlatAge: row.median_flat_age,
        transactions: row.transactions,
        budgetSlack: row.budget_slack,
        nearestMrtName: row.nearest_mrt_name,
        nearestMrtDistanceKm: row.nearest_mrt_distance_km,
        nearestBusStop: row.nearest_bus_stop != null ? String(row.nearest_bus_stop) : null,
        nearestBusStopDistanceKm: row.nearest_bus_stop_distance_km,
        schoolCountWithin1Km: row.school_count_within_1km,
        nearestSchool: row.nearest_school,
        nearestSchoolDistanceKm: row.nearest_school_distance_km,
        distanceToCbdKm: row.distance_to_cbd_km,
        score: candidateScore(row),
      } satisfies DashboardThreeCandidate
    })
    .sort(sortCandidates)

  const selectedBuilding =
    allCandidates.find((candidate) => candidate.buildingKey === query.buildingKey) ??
    allCandidates[0] ??
    null

  const candidates = allCandidates.slice(0, 120)

  const historyRows = selectedBuilding
    ? bundle.buildings
        .filter(
          (row) =>
            row.building_key === selectedBuilding.buildingKey &&
            row.budget === query.budget &&
            activeFlatTypes.includes(row.flat_type),
        )
        .map((row) => ({
          year: row.transaction_year,
          flatType: row.flat_type,
          transactions: row.transactions,
          medianPrice: row.median_price,
        }))
        .sort((left, right) => left.year - right.year || left.flatType.localeCompare(right.flatType))
    : []

  const nearbyAmenities = selectedBuilding
    ? bundle.poiPoints
        .map((poi) => ({
          poiType: poi.poi_type,
          poiName: poi.poi_name,
          latitude: poi.poi_latitude,
          longitude: poi.poi_longitude,
          distanceKm: haversineKm(
            selectedBuilding.latitude,
            selectedBuilding.longitude,
            poi.poi_latitude,
            poi.poi_longitude,
          ),
        }))
        .filter((poi) => poi.distanceKm <= 1.2)
        .sort((left, right) => left.distanceKm - right.distanceKm || left.poiName.localeCompare(right.poiName))
        .slice(0, 40)
    : []

  const prices = filteredRows.map((row) => row.median_price).filter((value) => Number.isFinite(value))
  const areas = filteredRows.map((row) => row.median_floor_area).filter((value) => Number.isFinite(value))

  return {
    town: bundle.town,
    filters: {
      year: query.year,
      budget: query.budget,
      flatTypes: activeFlatTypes,
      minFloorArea: query.minFloorArea,
      maxMrtDistanceKm: query.maxMrtDistanceKm,
      minSchoolCount: query.minSchoolCount,
    },
    summary: {
      shortlistCount: candidates.length,
      buildingRowsScanned: filteredRows.length,
      priceRange: prices.length > 0 ? [Math.min(...prices), Math.max(...prices)] : null,
      floorAreaRange: areas.length > 0 ? [Math.min(...areas), Math.max(...areas)] : null,
    },
    candidates,
    selectedBuildingKey: selectedBuilding?.buildingKey ?? null,
    selectedBuilding,
    history: historyRows,
    nearbyAmenities,
    geometry: bundle.geometry,
  }
}
