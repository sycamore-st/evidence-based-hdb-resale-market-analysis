import { NextResponse } from "next/server"

import { evaluateValuation, getValuationOptions } from "@/lib/section2-valuation"

function asFiniteNumber(value: unknown, fallback: number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export async function GET() {
  try {
    const options = await getValuationOptions()
    return NextResponse.json(options, {
      headers: {
        "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
      },
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to load valuation options."
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

export async function POST(request: Request) {
  const body = (await request.json()) as Record<string, unknown>

  const input = {
    transactionMonth: String(body.transactionMonth ?? ""),
    buildingKey: String(body.buildingKey ?? ""),
    floorAreaSqm: asFiniteNumber(body.floorAreaSqm, Number.NaN),
    leaseCommenceDate: asFiniteNumber(body.leaseCommenceDate, Number.NaN),
    minFloorLevel: asFiniteNumber(body.minFloorLevel, Number.NaN),
    maxFloorLevel: asFiniteNumber(body.maxFloorLevel, Number.NaN),
    flatModel: String(body.flatModel ?? ""),
    actualPrice:
      body.actualPrice === null || body.actualPrice === undefined || body.actualPrice === ""
        ? null
        : asFiniteNumber(body.actualPrice, Number.NaN),
  }

  if (
    !input.transactionMonth ||
    !input.buildingKey ||
    !Number.isFinite(input.floorAreaSqm) ||
    !Number.isFinite(input.leaseCommenceDate) ||
    !Number.isFinite(input.minFloorLevel) ||
    !Number.isFinite(input.maxFloorLevel) ||
    !input.flatModel
  ) {
    return NextResponse.json({ error: "Missing or invalid valuation input." }, { status: 400 })
  }

  try {
    const result = await evaluateValuation(input)
    return NextResponse.json(result)
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to evaluate valuation request."
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
