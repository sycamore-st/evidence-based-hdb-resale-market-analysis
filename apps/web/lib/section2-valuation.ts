import { readTextAsset, resolveRepositoryRawUrl } from "@/lib/server-data"

interface DistributionRow {
  flat_type: string
  town: string
  flat_model: string
  floor_area_sqm: number
  year: number
  age: number
  remaining_lease_years: number
  min_floor_level: number
  max_floor_level: number
  distance_to_cbd_km: number
  nearest_mrt_distance_km: number
  nearest_bus_stop_distance_km: number
  nearest_school_distance_km: number
  bus_stop_count_within_1km: number
  school_count_within_1km: number
  block: string
  street_name: string
  building_key: string
  building_latitude: number
  building_longitude: number
  resale_price: number
  transaction_month: string
  lease_commence_date: number
}

interface SubjectSummaryRow {
  town: string
  flat_type: string
  flat_model: string
  storey_range: string
  floor_area_sqm: number
  lease_commence_date: number
  transaction_month: string
  actual_price: number
  expected_price: number
}

export interface ValuationOptions {
  scope: string
  towns: string[]
  flatTypes: string[]
  flatModels: string[]
  months: string[]
  buildings: Array<{
    buildingKey: string
    block: string
    streetName: string
    label: string
  }>
  defaults: {
    transactionMonth: string
    buildingKey: string
    floorAreaSqm: number
    leaseCommenceDate: number
    minFloorLevel: number
    maxFloorLevel: number
    flatModel: string
    actualPrice: number
  }
}

export interface ValuationRequest {
  transactionMonth: string
  buildingKey: string
  floorAreaSqm: number
  leaseCommenceDate: number
  minFloorLevel: number
  maxFloorLevel: number
  flatModel: string
  actualPrice?: number | null
}

export interface ValuationComparable {
  id: string
  buildingKey: string
  block: string
  streetName: string
  transactionMonth: string
  flatModel: string
  floorAreaSqm: number
  resalePrice: number
  adjustedPrice: number
  geoDistanceKm: number
  areaGapSqm: number
  ageGapYears: number
  score: number
}

export interface ValuationResult {
  scope: string
  subject: {
    transactionMonth: string
    buildingKey: string
    floorAreaSqm: number
    leaseCommenceDate: number
    minFloorLevel: number
    maxFloorLevel: number
    flatModel: string
    actualPrice: number | null
  }
  metrics: {
    expectedPrice: number
    modelEstimate: number
    comparablesEstimate: number | null
    intervalLow: number
    intervalHigh: number
    localP025: number
    localP25: number
    localP50: number
    localP75: number
    localP975: number
    comparablesCount: number
    localCount: number
  }
  decision: {
    confidence: "High" | "Moderate" | "Limited"
    verdict: "Likely Overpriced" | "Likely Underpriced" | "Within Expected Range" | "Insufficient Price Input"
    deviationPct: number | null
    deviationAmount: number | null
    note: string
  }
  comparables: ValuationComparable[]
  chartData: {
    histogramPrices: number[]
    comparableArea: number[]
    comparablePrice: number[]
    comparableLabels: string[]
  }
}

interface ValuationDataset {
  rows: DistributionRow[]
  byBuilding: Map<string, DistributionRow[]>
  options: ValuationOptions
}

const RESULTS_BASE = "outputs/section2/results"
const DISTRIBUTION_CONTEXTS_CSV = `${RESULTS_BASE}/S2Qb_distribution_contexts.csv`
const SUBJECT_SUMMARY_CSV = `${RESULTS_BASE}/S2Qb_subject_summary.csv`

let cachedDataset: Promise<ValuationDataset> | null = null

function parseCsvLine(line: string): string[] {
  const values: string[] = []
  let current = ""
  let inQuotes = false

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index]
    if (char === "\"") {
      if (inQuotes && line[index + 1] === "\"") {
        current += "\""
        index += 1
      } else {
        inQuotes = !inQuotes
      }
      continue
    }
    if (char === "," && !inQuotes) {
      values.push(current)
      current = ""
      continue
    }
    current += char
  }
  values.push(current)
  return values
}

function toNumber(value: string | undefined): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : Number.NaN
}

function monthDiff(aIsoMonthStart: string, bIsoMonthStart: string): number {
  const a = new Date(aIsoMonthStart)
  const b = new Date(bIsoMonthStart)
  return Math.abs((a.getUTCFullYear() - b.getUTCFullYear()) * 12 + (a.getUTCMonth() - b.getUTCMonth()))
}

function quantile(values: number[], q: number): number {
  if (values.length === 0) {
    return Number.NaN
  }
  const sorted = [...values].sort((left, right) => left - right)
  const position = (sorted.length - 1) * q
  const base = Math.floor(position)
  const rest = position - base
  if (sorted[base + 1] === undefined) {
    return sorted[base]
  }
  return sorted[base] + rest * (sorted[base + 1] - sorted[base])
}

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const toRadians = (value: number) => (value * Math.PI) / 180
  const earthRadiusKm = 6371
  const dLat = toRadians(lat2 - lat1)
  const dLon = toRadians(lon2 - lon1)
  const startLat = toRadians(lat1)
  const endLat = toRadians(lat2)

  const a = Math.sin(dLat / 2) ** 2 + Math.sin(dLon / 2) ** 2 * Math.cos(startLat) * Math.cos(endLat)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return earthRadiusKm * c
}

function formatMonth(value: string): string {
  return value.slice(0, 7)
}

function buildDefaultOptions(rows: DistributionRow[], subject: SubjectSummaryRow): ValuationOptions {
  const months = Array.from(new Set(rows.map((row) => row.transaction_month.slice(0, 7)))).sort()
  const flatModels = Array.from(new Set(rows.map((row) => row.flat_model))).sort((left, right) => left.localeCompare(right))
  const buildings = Array.from(
    rows.reduce((memo, row) => {
      if (!memo.has(row.building_key)) {
        memo.set(row.building_key, {
          buildingKey: row.building_key,
          block: row.block,
          streetName: row.street_name,
          label: `${row.block} ${row.street_name} (${row.building_key})`,
        })
      }
      return memo
    }, new Map<string, { buildingKey: string; block: string; streetName: string; label: string }>())
      .values()
  ).sort((left, right) => left.label.localeCompare(right.label))

  const defaultBuilding =
    buildings.find((item) => item.buildingKey === "790|760790") ??
    buildings.find((item) => item.label.includes("YISHUN")) ??
    buildings[0]

  return {
    scope: "Question B extended cohort: Yishun 4-room transactions (2015-2018) from Section 2 artifacts.",
    towns: ["YISHUN"],
    flatTypes: ["4 ROOM"],
    flatModels,
    months,
    buildings,
    defaults: {
      transactionMonth: subject.transaction_month.slice(0, 7),
      buildingKey: defaultBuilding?.buildingKey ?? "",
      floorAreaSqm: subject.floor_area_sqm,
      leaseCommenceDate: subject.lease_commence_date,
      minFloorLevel: 10,
      maxFloorLevel: 12,
      flatModel: subject.flat_model,
      actualPrice: subject.actual_price,
    },
  }
}

async function loadRowsFromCsv(): Promise<DistributionRow[]> {
  const raw = await readSectionTextAsset(DISTRIBUTION_CONTEXTS_CSV)
  const lines = raw.split(/\r?\n/).filter((line) => line.length > 0)
  if (lines.length <= 1) {
    return []
  }

  const headers = parseCsvLine(lines[0])
  const records: DistributionRow[] = []

  for (const line of lines.slice(1)) {
    const fields = parseCsvLine(line)
    const row = Object.fromEntries(headers.map((header, index) => [header, fields[index] ?? ""]))
    const month = row.transaction_month
    if (!month) {
      continue
    }
    records.push({
      flat_type: row.flat_type,
      town: row.town,
      flat_model: row.flat_model,
      floor_area_sqm: toNumber(row.floor_area_sqm),
      year: toNumber(row.year),
      age: toNumber(row.age),
      remaining_lease_years: toNumber(row.remaining_lease_years),
      min_floor_level: toNumber(row.min_floor_level),
      max_floor_level: toNumber(row.max_floor_level),
      distance_to_cbd_km: toNumber(row.distance_to_cbd_km),
      nearest_mrt_distance_km: toNumber(row.nearest_mrt_distance_km),
      nearest_bus_stop_distance_km: toNumber(row.nearest_bus_stop_distance_km),
      nearest_school_distance_km: toNumber(row.nearest_school_distance_km),
      bus_stop_count_within_1km: toNumber(row.bus_stop_count_within_1km),
      school_count_within_1km: toNumber(row.school_count_within_1km),
      block: row.block,
      street_name: row.street_name,
      building_key: row.building_key,
      building_latitude: toNumber(row.building_latitude),
      building_longitude: toNumber(row.building_longitude),
      resale_price: toNumber(row.resale_price),
      transaction_month: row.transaction_month,
      lease_commence_date: toNumber(row.lease_commence_date),
    })
  }
  return records
}

async function loadSubjectSummary(): Promise<SubjectSummaryRow> {
  const raw = await readSectionTextAsset(SUBJECT_SUMMARY_CSV)
  const lines = raw.split(/\r?\n/).filter((line) => line.length > 0)
  const headers = parseCsvLine(lines[0])
  const values = parseCsvLine(lines[1] ?? "")
  const row = Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]))

  return {
    town: row.town,
    flat_type: row.flat_type,
    flat_model: row.flat_model,
    storey_range: row.storey_range,
    floor_area_sqm: toNumber(row.floor_area_sqm),
    lease_commence_date: toNumber(row.lease_commence_date),
    transaction_month: row.transaction_month,
    actual_price: toNumber(row.actual_price),
    expected_price: toNumber(row.expected_price),
  }
}

async function readSectionTextAsset(relativePath: string): Promise<string> {
  try {
    return await readTextAsset(relativePath)
  } catch (error) {
    const fallbackUrl = resolveRepositoryRawUrl(relativePath)
    const response = await fetch(fallbackUrl, { cache: "no-store" })
    if (!response.ok) {
      const reason = error instanceof Error ? error.message : "unknown local read error"
      throw new Error(
        `Unable to load ${relativePath}. Local read failed (${reason}) and fallback fetch failed (${response.status} ${response.statusText}).`
      )
    }
    return response.text()
  }
}

async function loadDataset(): Promise<ValuationDataset> {
  if (!cachedDataset) {
    cachedDataset = (async () => {
      const [rows, subject] = await Promise.all([loadRowsFromCsv(), loadSubjectSummary()])
      const byBuilding = rows.reduce((memo, row) => {
        const current = memo.get(row.building_key) ?? []
        current.push(row)
        memo.set(row.building_key, current)
        return memo
      }, new Map<string, DistributionRow[]>())

      return {
        rows,
        byBuilding,
        options: buildDefaultOptions(rows, subject),
      }
    })()
  }
  return cachedDataset
}

function findAnchorRow(dataset: ValuationDataset, request: ValuationRequest): DistributionRow {
  const monthStart = `${request.transactionMonth}-01`
  const buildingRows = dataset.byBuilding.get(request.buildingKey) ?? []

  if (buildingRows.length === 0) {
    throw new Error(`Unknown building key: ${request.buildingKey}`)
  }

  const exactMonth = buildingRows.find((row) => formatMonth(row.transaction_month) === request.transactionMonth)
  if (exactMonth) {
    return exactMonth
  }

  return [...buildingRows].sort(
    (left, right) => monthDiff(left.transaction_month, monthStart) - monthDiff(right.transaction_month, monthStart)
  )[0]
}

function buildComparableScore(
  row: DistributionRow,
  anchorRow: DistributionRow,
  request: ValuationRequest,
  transactionMonth: string
): number {
  const targetAge = Number(transactionMonth.slice(0, 4)) - request.leaseCommenceDate
  const targetMidFloor = (request.minFloorLevel + request.maxFloorLevel) / 2
  const rowMidFloor = (row.min_floor_level + row.max_floor_level) / 2

  const geoDistance = haversineKm(
    anchorRow.building_latitude,
    anchorRow.building_longitude,
    row.building_latitude,
    row.building_longitude
  )
  const areaGap = Math.abs(row.floor_area_sqm - request.floorAreaSqm)
  const ageGap = Math.abs(row.age - targetAge)
  const floorGap = Math.abs(rowMidFloor - targetMidFloor)
  const monthGap = monthDiff(row.transaction_month, `${transactionMonth}-01`)
  const modelPenalty = row.flat_model === request.flatModel ? 0 : 0.65

  return areaGap / 9 + ageGap / 5 + floorGap / 5 + monthGap / 6 + geoDistance / 1.2 + modelPenalty
}

export async function getValuationOptions(): Promise<ValuationOptions> {
  const dataset = await loadDataset()
  return dataset.options
}

export async function evaluateValuation(request: ValuationRequest): Promise<ValuationResult> {
  const dataset = await loadDataset()
  const anchorRow = findAnchorRow(dataset, request)
  const transactionMonth = request.transactionMonth

  const candidateRows = dataset.rows
    .filter((row) => monthDiff(row.transaction_month, `${transactionMonth}-01`) <= 24)
    .map((row) => ({
      row,
      score: buildComparableScore(row, anchorRow, request, transactionMonth),
      geoDistanceKm: haversineKm(
        anchorRow.building_latitude,
        anchorRow.building_longitude,
        row.building_latitude,
        row.building_longitude
      ),
    }))
    .sort((left, right) => left.score - right.score)

  const modelPool = candidateRows.slice(0, 160)
  const modelWeights = modelPool.map((item) => Math.exp(-item.score * 0.7))
  const modelWeightSum = modelWeights.reduce((sum, value) => sum + value, 0)
  const modelEstimate =
    modelWeightSum > 0
      ? modelPool.reduce((sum, item, index) => sum + item.row.resale_price * modelWeights[index], 0) / modelWeightSum
      : Number.NaN

  const comparablePool = candidateRows
    .filter((item) => item.geoDistanceKm <= 3.2 && Math.abs(item.row.floor_area_sqm - request.floorAreaSqm) <= 14)
    .slice(0, 12)

  const comparables: ValuationComparable[] = comparablePool.map((item, index) => ({
    id: [
      item.row.building_key,
      item.row.transaction_month,
      item.row.resale_price.toFixed(0),
      item.row.floor_area_sqm.toFixed(1),
      item.score.toFixed(6),
      item.row.block,
      item.row.street_name,
      String(index),
    ].join("|"),
    buildingKey: item.row.building_key,
    block: item.row.block,
    streetName: item.row.street_name,
    transactionMonth: item.row.transaction_month.slice(0, 7),
    flatModel: item.row.flat_model,
    floorAreaSqm: item.row.floor_area_sqm,
    resalePrice: item.row.resale_price,
    adjustedPrice:
      item.row.floor_area_sqm > 0 ? item.row.resale_price * (request.floorAreaSqm / item.row.floor_area_sqm) : item.row.resale_price,
    geoDistanceKm: item.geoDistanceKm,
    areaGapSqm: Math.abs(item.row.floor_area_sqm - request.floorAreaSqm),
    ageGapYears: Math.abs(item.row.age - (Number(transactionMonth.slice(0, 4)) - request.leaseCommenceDate)),
    score: item.score,
  }))

  const comparableAdjustedPrices = comparables.map((item) => item.adjustedPrice)
  const comparablesEstimate = comparables.length > 0 ? quantile(comparableAdjustedPrices, 0.5) : null

  const localPool = dataset.rows.filter((row) => {
    const nearby = haversineKm(
      anchorRow.building_latitude,
      anchorRow.building_longitude,
      row.building_latitude,
      row.building_longitude
    )
    const closeByMonth = monthDiff(row.transaction_month, `${transactionMonth}-01`) <= 8
    const closeByArea = Math.abs(row.floor_area_sqm - request.floorAreaSqm) <= 15
    return nearby <= 3 && closeByMonth && closeByArea
  })

  const localPrices = localPool.map((row) => row.resale_price)
  const localP025 = quantile(localPrices, 0.025)
  const localP25 = quantile(localPrices, 0.25)
  const localP50 = quantile(localPrices, 0.5)
  const localP75 = quantile(localPrices, 0.75)
  const localP975 = quantile(localPrices, 0.975)

  const expectedPrice =
    comparablesEstimate !== null && Number.isFinite(modelEstimate)
      ? modelEstimate * 0.6 + comparablesEstimate * 0.4
      : Number.isFinite(modelEstimate)
        ? modelEstimate
        : comparablesEstimate ?? anchorRow.resale_price

  const intervalLow = Number.isFinite(localP025) ? localP025 : expectedPrice * 0.86
  const intervalHigh = Number.isFinite(localP975) ? localP975 : expectedPrice * 1.14

  const confidence: "High" | "Moderate" | "Limited" =
    comparables.length >= 8 && localPool.length >= 90
      ? "High"
      : comparables.length >= 4 && localPool.length >= 45
        ? "Moderate"
        : "Limited"

  const hasActualPrice = typeof request.actualPrice === "number" && Number.isFinite(request.actualPrice)
  const deviationAmount = hasActualPrice ? request.actualPrice! - expectedPrice : null
  const deviationPct = hasActualPrice && expectedPrice > 0 ? deviationAmount! / expectedPrice : null
  const verdict: ValuationResult["decision"]["verdict"] = !hasActualPrice
    ? "Insufficient Price Input"
    : deviationPct! >= 0.1
      ? "Likely Overpriced"
      : deviationPct! <= -0.1
        ? "Likely Underpriced"
        : "Within Expected Range"

  return {
    scope: dataset.options.scope,
    subject: {
      transactionMonth,
      buildingKey: request.buildingKey,
      floorAreaSqm: request.floorAreaSqm,
      leaseCommenceDate: request.leaseCommenceDate,
      minFloorLevel: request.minFloorLevel,
      maxFloorLevel: request.maxFloorLevel,
      flatModel: request.flatModel,
      actualPrice: hasActualPrice ? request.actualPrice! : null,
    },
    metrics: {
      expectedPrice,
      modelEstimate,
      comparablesEstimate,
      intervalLow,
      intervalHigh,
      localP025,
      localP25,
      localP50,
      localP75,
      localP975,
      comparablesCount: comparables.length,
      localCount: localPool.length,
    },
    decision: {
      confidence,
      verdict,
      deviationPct,
      deviationAmount,
      note:
        confidence === "Limited"
          ? "Comparable and local support are thin. Treat this as directional only."
          : "Evidence is internally consistent across expected price, local distribution, and comparables.",
    },
    comparables,
    chartData: {
      histogramPrices: localPrices,
      comparableArea: comparables.map((item) => item.floorAreaSqm),
      comparablePrice: comparables.map((item) => item.resalePrice),
      comparableLabels: comparables.map((item) => `${item.block} ${item.streetName} (${item.transactionMonth})`),
    },
  }
}
