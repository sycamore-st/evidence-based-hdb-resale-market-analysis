import { DashboardTwoExplorer } from "@/components/section1/dashboard-two-explorer"
import { loadDashboardTwoData } from "@/lib/section1-dashboard2"

export default function DashboardTwoPage() {
  const data = loadDashboardTwoData()

  return <DashboardTwoExplorer data={data} />
}
