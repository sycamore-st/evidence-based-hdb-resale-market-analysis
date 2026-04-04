import { DashboardOneExplorer, type DashboardOneLayoutPreset } from "@/components/section1/dashboard-one-explorer"
import { loadDashboardOneData } from "@/lib/section1-dashboard1"

function normalizeLayoutPreset(raw: string | undefined): DashboardOneLayoutPreset {
  if (raw === "editorial" || raw === "balanced" || raw === "chart-heavy" || raw === "map-heavy" || raw === "stacked") {
    return raw
  }
  return "balanced"
}

export default async function DashboardOnePage({
  searchParams,
}: {
  searchParams: Promise<{ layout?: string }>
}) {
  const data = loadDashboardOneData()
  const params = await searchParams
  const layoutPreset = normalizeLayoutPreset(params.layout)

  return <DashboardOneExplorer data={data} layoutPreset={layoutPreset} />
}
