import { DashboardThreeExplorer } from "@/components/section1/dashboard-three-explorer"
import { buildDashboardThreeTownPayload, defaultDashboardThreeQuery, loadDashboardThreeManifest } from "@/lib/section1-dashboard3"

export default async function DashboardThreePage() {
  const manifest = await loadDashboardThreeManifest()
  const initialPayload = await buildDashboardThreeTownPayload(await defaultDashboardThreeQuery())

  return <DashboardThreeExplorer manifest={manifest} initialPayload={initialPayload} />
}
