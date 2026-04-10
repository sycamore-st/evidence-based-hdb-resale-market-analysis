import type { DashboardSection } from "@/lib/theme"
import { readJsonAsset } from "@/lib/server-data"

export interface SummaryCard {
  id: string
  label: string
  value: string
  context: string
}

export interface DashboardSummary {
  dataset_version: string
  generated_at: string
  source_coverage_end: string
  headline: string
  description: string
  cards: SummaryCard[]
  insights: string[]
}

export interface DataPoint {
  x: string
  y: number
}

export interface ChartSeries {
  id: string
  label: string
  points: DataPoint[]
}

export interface DashboardTimeseries {
  dataset_version: string
  generated_at: string
  source_coverage_end: string
  series: ChartSeries[]
}

export interface DashboardFilters {
  dataset_version: string
  generated_at: string
  source_coverage_end: string
  filters: Array<{
    id: string
    label: string
    options: string[]
  }>
}

export interface DashboardMetadata {
  dataset_version: string
  generated_at: string
  source_coverage_end: string
  section: DashboardSection
  record_count: number
  notes: string[]
}

export interface DashboardBundle {
  summary: DashboardSummary
  timeseries: DashboardTimeseries
  filters: DashboardFilters
  metadata: DashboardMetadata
}

function isMissingAssetError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false
  }
  const maybeCode = (error as NodeJS.ErrnoException).code
  return maybeCode === "ENOENT" || error.message.includes("Unable to load")
}

function fallbackBundle(section: DashboardSection): DashboardBundle {
  const now = new Date().toISOString()
  return {
    summary: {
      dataset_version: "unavailable",
      generated_at: now,
      source_coverage_end: "N/A",
      headline: "Data Artifact Unavailable",
      description: "This preview deployment does not include local artifact JSON files.",
      cards: [],
      insights: [
        "Preview build uses fallback content when artifact files are not present.",
        "Run the data build pipeline and redeploy to restore full dashboard content.",
      ],
    },
    timeseries: {
      dataset_version: "unavailable",
      generated_at: now,
      source_coverage_end: "N/A",
      series: [],
    },
    filters: {
      dataset_version: "unavailable",
      generated_at: now,
      source_coverage_end: "N/A",
      filters: [],
    },
    metadata: {
      dataset_version: "unavailable",
      generated_at: now,
      source_coverage_end: "N/A",
      section,
      record_count: 0,
      notes: [
        "Artifact payload missing in deployment bundle.",
        "Fallback mode prevents build failure for preview environments.",
      ],
    },
  }
}

async function readJson<T>(section: DashboardSection, name: string): Promise<T> {
  return readJsonAsset<T>(`artifacts/web/${section}/${name}.json`)
}

export async function readDashboardBundle(section: DashboardSection): Promise<DashboardBundle> {
  try {
    const [summary, timeseries, filters, metadata] = await Promise.all([
      readJson<DashboardSummary>(section, "summary"),
      readJson<DashboardTimeseries>(section, "timeseries"),
      readJson<DashboardFilters>(section, "filters"),
      readJson<DashboardMetadata>(section, "metadata"),
    ])

    return { summary, timeseries, filters, metadata }
  } catch (error) {
    if (!isMissingAssetError(error)) {
      throw error
    }
    return fallbackBundle(section)
  }
}
