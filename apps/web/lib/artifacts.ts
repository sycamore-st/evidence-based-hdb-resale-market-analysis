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

async function readJson<T>(section: DashboardSection, name: string): Promise<T> {
  return readJsonAsset<T>(`artifacts/web/${section}/${name}.json`)
}

export async function readDashboardBundle(section: DashboardSection): Promise<DashboardBundle> {
  const [summary, timeseries, filters, metadata] = await Promise.all([
    readJson<DashboardSummary>(section, "summary"),
    readJson<DashboardTimeseries>(section, "timeseries"),
    readJson<DashboardFilters>(section, "filters"),
    readJson<DashboardMetadata>(section, "metadata")
  ])

  return { summary, timeseries, filters, metadata }
}
