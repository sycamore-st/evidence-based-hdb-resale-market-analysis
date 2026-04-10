import { readTextAsset } from "@/lib/server-data"

export interface DashboardTwoRow {
  year: number
  town: string
  flatType: string
  transactions: number
  minPrice: number
  medianPrice: number
  maxPrice: number
  minFloorArea: number
  medianFloorArea: number
  maxFloorArea: number
  budget: number
  budgetSlack: number
}

export interface DashboardTwoMetricRow {
  year: number
  town: string
  flatType: string
  budget: number
  metric: "Min" | "P25" | "Median" | "P75" | "Max"
  price: number
  floorArea: number
}

export interface DashboardTwoLegendItem {
  panel: "Floor Area" | "Price"
  metric: "Min" | "Median" | "Max"
  value: number
  note: string
}

export interface DashboardTwoData {
  years: number[]
  budgets: number[]
  towns: string[]
  rows: DashboardTwoRow[]
  metricRows: DashboardTwoMetricRow[]
  legend: DashboardTwoLegendItem[]
}

const BUDGET_AFFORDABILITY_CSV = "outputs/section1/results/final/budget_affordability.csv"
const BUDGET_METRICS_CSV = "outputs/section1/results/final/budget_affordability_metrics.csv"
const BUDGET_LEGEND_CSV = "outputs/section1/results/final/budget_affordability_legend.csv"

function isMissingAssetError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false
  }
  const maybeCode = (error as NodeJS.ErrnoException).code
  return maybeCode === "ENOENT" || error.message.includes("Unable to load")
}

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
  if (!headerLine) {
    return []
  }
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
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

export async function loadDashboardTwoData(): Promise<DashboardTwoData> {
  let affordabilityCsv = ""
  let metricsCsv = ""
  let legendCsv = ""
  try {
    ;[affordabilityCsv, metricsCsv, legendCsv] = await Promise.all([
      readTextAsset(BUDGET_AFFORDABILITY_CSV),
      readTextAsset(BUDGET_METRICS_CSV),
      readTextAsset(BUDGET_LEGEND_CSV),
    ])
  } catch (error) {
    if (!isMissingAssetError(error)) {
      throw error
    }
    return {
      years: [],
      budgets: [],
      towns: [],
      rows: [],
      metricRows: [],
      legend: [],
    }
  }

  const rows = parseCsv(affordabilityCsv).map<DashboardTwoRow>((row) => ({
    year: toNumber(row["Transaction Year"]),
    town: row["Town"],
    flatType: row["Flat Type"],
    transactions: toNumber(row["Transactions"]),
    minPrice: toNumber(row["min_price"]),
    medianPrice: toNumber(row["Median Price"]),
    maxPrice: toNumber(row["max_price"]),
    minFloorArea: toNumber(row["min_floor_area"]),
    medianFloorArea: toNumber(row["Median Floor Area"]),
    maxFloorArea: toNumber(row["max_floor_area"]),
    budget: toNumber(row["Budget"]),
    budgetSlack: toNumber(row["Budget Slack"]),
  }))

  const metricRows = parseCsv(metricsCsv).map<DashboardTwoMetricRow>((row) => ({
    year: toNumber(row["Transaction Year"]),
    town: row["Town"],
    flatType: row["Flat Type"],
    budget: toNumber(row["Budget"]),
    metric: (row["Metric"] as "Min" | "P25" | "Median" | "P75" | "Max") ?? "Median",
    price: toNumber(row["Price"]),
    floorArea: toNumber(row["Floor Area"]),
  }))

  const legend = parseCsv(legendCsv).map<DashboardTwoLegendItem>((row) => ({
    panel: (row["Legend Panel"] as "Floor Area" | "Price") ?? "Floor Area",
    metric: (row["Metric"] as "Min" | "Median" | "Max") ?? "Median",
    value: toNumber(row["Legend Value"]),
    note: row["Legend Note"],
  }))

  const years = Array.from(new Set(rows.map((row) => row.year))).sort((left, right) => right - left)
  const budgets = Array.from(new Set(rows.map((row) => row.budget))).sort((left, right) => left - right)
  const towns = Array.from(new Set(rows.map((row) => row.town))).sort((left, right) => left.localeCompare(right))

  return { years, budgets, towns, rows, metricRows, legend }
}
