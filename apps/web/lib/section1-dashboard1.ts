import { readJsonAsset, readTextAsset } from "@/lib/server-data"

export interface DashboardOneRow {
  year: number
  town: string
  flatType: string
  transactions: number
  medianPrice: number
  regionKey: string
  regionLabel: string
  regionType: string
}

export interface MapShape {
  regionKey: string
  regionLabel: string
  regionType: string
  town: string | null
  path: string
}

export interface DashboardOneData {
  years: number[]
  flatTypes: string[]
  rows: DashboardOneRow[]
  mapShapes: MapShape[]
}

type GeoFeature = {
  geometry: {
    type: "Polygon" | "MultiPolygon"
    coordinates: number[][][] | number[][][][]
  }
  properties: {
    Town?: string | null
    "Region Key"?: string
    "Region Label"?: string
    "Region Type"?: string
  }
}

const DASHBOARD_CSV = "outputs/section1/results/final/dashboard_market_overview.csv"
const MAP_GEOJSON = "outputs/section1/results/final/planning_area_hdb_map_2019.geojson"

function parseCsvRow(line: string): string[] {
  const cells: string[] = []
  let current = ""
  let inQuotes = false

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index]
    const next = line[index + 1]

    if (char === '"') {
      if (inQuotes && next === '"') {
        current += '"'
        index += 1
      } else {
        inQuotes = !inQuotes
      }
      continue
    }

    if (char === "," && !inQuotes) {
      cells.push(current)
      current = ""
      continue
    }

    current += char
  }

  cells.push(current)
  return cells
}

function parseCsv(content: string): Array<Record<string, string>> {
  const lines = content.split(/\r?\n/).filter((line) => line.length > 0)
  const [headerLine, ...dataLines] = lines
  const headers = parseCsvRow(headerLine)

  return dataLines.map((line) => {
    const values = parseCsvRow(line)
    return headers.reduce<Record<string, string>>((row, header, index) => {
      row[header] = values[index] ?? ""
      return row
    }, {})
  })
}

function toNumber(value: string): number {
  if (!value) {
    return 0
  }

  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

async function readDashboardRows(): Promise<DashboardOneRow[]> {
  const csv = await readTextAsset(DASHBOARD_CSV)
  const rows = parseCsv(csv)

  return rows.map((row) => ({
    year: Number(row["Transaction Year"]),
    town: row["Town"],
    flatType: row["Flat Type"],
    transactions: toNumber(row["Transactions"]),
    medianPrice: toNumber(row["Median Price"]),
    regionKey: row["Region Key"],
    regionLabel: row["Region Label"],
    regionType: row["Region Type"],
  }))
}

function flattenRingPoints(geometry: GeoFeature["geometry"]): Array<[number, number]> {
  if (geometry.type === "Polygon") {
    return (geometry.coordinates as number[][][]).flatMap((ring) => ring.map(([x, y]) => [x, y] as [number, number]))
  }

  return (geometry.coordinates as number[][][][]).flatMap((polygon) =>
    polygon.flatMap((ring) => ring.map(([x, y]) => [x, y] as [number, number])),
  )
}

function buildPath(
  geometry: GeoFeature["geometry"],
  project: (point: [number, number]) => [number, number],
): string {
  const polygonToPath = (polygon: number[][][]) =>
    polygon
      .map((ring) =>
        ring
          .map(([lon, lat], pointIndex) => {
            const [x, y] = project([lon, lat])
            return `${pointIndex === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`
          })
          .join(" ") + " Z",
      )
      .join(" ")

  if (geometry.type === "Polygon") {
    return polygonToPath(geometry.coordinates as number[][][])
  }

  return (geometry.coordinates as number[][][][]).map((polygon) => polygonToPath(polygon)).join(" ")
}

async function readMapShapes(): Promise<MapShape[]> {
  const geojson = await readJsonAsset<{ features: GeoFeature[] }>(MAP_GEOJSON)
  const allPoints = geojson.features.flatMap((feature) => flattenRingPoints(feature.geometry))
  const xs = allPoints.map(([x]) => x)
  const ys = allPoints.map(([, y]) => y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const width = 540
  const height = 420
  const padding = 18
  const scale = Math.min((width - padding * 2) / (maxX - minX), (height - padding * 2) / (maxY - minY))
  const offsetX = (width - (maxX - minX) * scale) / 2
  const offsetY = (height - (maxY - minY) * scale) / 2

  const project = ([lon, lat]: [number, number]): [number, number] => [
    (lon - minX) * scale + offsetX,
    height - ((lat - minY) * scale + offsetY),
  ]

  return geojson.features.map((feature) => ({
    regionKey: feature.properties["Region Key"] ?? feature.properties["Region Label"] ?? "unknown",
    regionLabel: feature.properties["Region Label"] ?? feature.properties["Region Key"] ?? "Unknown",
    regionType: feature.properties["Region Type"] ?? "unknown",
    town: feature.properties.Town ?? null,
    path: buildPath(feature.geometry, project),
  }))
}

export async function loadDashboardOneData(): Promise<DashboardOneData> {
  const rows = await readDashboardRows()
  const flatTypes = rows
    .map((row) => row.flatType)
    .filter((value, index, all) => all.indexOf(value) === index)
    .sort((left, right) => {
      if (left === "ALL FLAT TYPE") return -1
      if (right === "ALL FLAT TYPE") return 1
      return left.localeCompare(right)
    })
  const years = rows
    .map((row) => row.year)
    .filter((value, index, all) => all.indexOf(value) === index)
    .sort((left, right) => right - left)

  return {
    years,
    flatTypes,
    rows,
    mapShapes: await readMapShapes(),
  }
}
