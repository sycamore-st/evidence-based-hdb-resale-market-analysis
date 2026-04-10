import { DashboardOneExplorer } from "@/components/section1/dashboard-one-explorer"
import { loadDashboardOneData } from "@/lib/section1-dashboard1"

export const dynamic = "force-static"

export default async function DashboardOnePage() {
  const data = await loadDashboardOneData()

  return <DashboardOneExplorer data={data} layoutPreset="balanced" />
}
