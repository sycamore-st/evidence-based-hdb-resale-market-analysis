import { DashboardThreeExplorer } from "@/components/section1/dashboard-three-explorer"
import { buildDashboardThreeTownPayload, defaultDashboardThreeQuery, loadDashboardThreeManifest } from "@/lib/section1-dashboard3"

export default function DashboardThreePage() {
  const manifest = loadDashboardThreeManifest()
  const initialPayload = buildDashboardThreeTownPayload(defaultDashboardThreeQuery())

  return <DashboardThreeExplorer manifest={manifest} initialPayload={initialPayload} />
}
