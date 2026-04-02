import { DashboardOneSandbox } from "@/components/section1/dashboard-one-sandbox"
import { loadDashboardOneData } from "@/lib/section1-dashboard1"
import { buildSandboxInitial } from "@/lib/section1-dashboard1-sandbox"

function normalizeSearch(
  params: Record<string, string | string[] | undefined>,
): Record<string, string | undefined> {
  return Object.fromEntries(
    Object.entries(params).map(([key, value]) => [key, Array.isArray(value) ? value[0] : value]),
  )
}

export default async function DashboardOneSandboxPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}) {
  const data = loadDashboardOneData()
  const params = await searchParams
  const initial = buildSandboxInitial(normalizeSearch(params))

  return <DashboardOneSandbox data={data} initial={initial} />
}
