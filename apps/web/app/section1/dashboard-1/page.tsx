import { DashboardOneExplorer } from "@/components/section1/dashboard-one-explorer"
import { loadDashboardOneData } from "@/lib/section1-dashboard1"

export default async function DashboardOnePage({
  searchParams,
}: {
  searchParams: Promise<{ layout?: string }>
}) {
  const data = await loadDashboardOneData()
  await searchParams

  return <DashboardOneExplorer data={data} layoutPreset="balanced" />
}
