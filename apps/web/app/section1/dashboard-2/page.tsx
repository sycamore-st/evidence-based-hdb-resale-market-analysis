import { DashboardTwoExplorer } from "@/components/section1/dashboard-two-explorer"
import { loadDashboardTwoData } from "@/lib/section1-dashboard2"

export default async function DashboardTwoPage() {
  const data = await loadDashboardTwoData()

  return <DashboardTwoExplorer data={data} />
}
