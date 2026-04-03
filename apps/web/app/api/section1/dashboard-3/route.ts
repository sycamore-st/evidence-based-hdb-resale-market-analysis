import { NextResponse } from "next/server"

import { buildDashboardThreeTownPayload, defaultDashboardThreeQuery, loadDashboardThreeManifest } from "@/lib/section1-dashboard3"

function parseNumber(value: string | null, fallback: number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export async function GET(request: Request) {
  const url = new URL(request.url)
  const manifest = loadDashboardThreeManifest()
  const defaults = defaultDashboardThreeQuery()

  const slug = url.searchParams.get("slug") ?? defaults.slug
  const town = manifest.towns.find((item) => item.slug === slug) ?? manifest.towns[0]

  const query = {
    slug: town.slug,
    year: parseNumber(url.searchParams.get("year"), defaults.year),
    budget: parseNumber(url.searchParams.get("budget"), defaults.budget),
    flatTypes: url.searchParams.getAll("flatType").filter((value) => value.length > 0),
    minFloorArea: parseNumber(url.searchParams.get("minFloorArea"), defaults.minFloorArea),
    maxMrtDistanceKm: parseNumber(url.searchParams.get("maxMrtDistanceKm"), defaults.maxMrtDistanceKm),
    minSchoolCount: parseNumber(url.searchParams.get("minSchoolCount"), defaults.minSchoolCount),
    buildingKey: url.searchParams.get("buildingKey"),
  }

  const payload = buildDashboardThreeTownPayload({
    ...query,
    flatTypes: query.flatTypes.length > 0 ? query.flatTypes : town.filters.flat_types,
  })

  return NextResponse.json(payload)
}
