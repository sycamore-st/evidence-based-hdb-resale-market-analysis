export type DashboardOneLayoutPreset = "editorial" | "balanced" | "chart-heavy"
export type DashboardOneMapSide = "left" | "right"
export type DashboardOneRightPanel = "legend" | "bars" | "lines"

export type DashboardOneSandboxState = {
  layout: DashboardOneLayoutPreset
  mapSide: DashboardOneMapSide
  rightOrder: DashboardOneRightPanel[]
  mapMaxWidth: number
  layoutGap: number
  panelPadding: number
  leftMinPx: number
  leftFr: number
  rightFr: number
  barHeight: number
  lineHeight: number
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function numberFromQuery(raw: string | undefined, fallback: number, min: number, max: number): number {
  const parsed = Number(raw)
  if (!Number.isFinite(parsed)) {
    return fallback
  }
  return clamp(parsed, min, max)
}

function parseRightOrder(raw: string | undefined): DashboardOneRightPanel[] {
  const defaultOrder: DashboardOneRightPanel[] = ["legend", "bars", "lines"]
  if (!raw) {
    return defaultOrder
  }
  const parsed = raw.split(",").filter(Boolean) as DashboardOneRightPanel[]
  const allowed: DashboardOneRightPanel[] = ["legend", "bars", "lines"]
  const unique = parsed.filter((item, index) => allowed.includes(item) && parsed.indexOf(item) === index)
  const missing = allowed.filter((item) => !unique.includes(item))
  return [...unique, ...missing].slice(0, 3)
}

export function buildSandboxInitial(search: { [key: string]: string | undefined }): DashboardOneSandboxState {
  const layout: DashboardOneLayoutPreset =
    search.layout === "editorial" || search.layout === "balanced" || search.layout === "chart-heavy"
      ? search.layout
      : "balanced"

  return {
    layout,
    mapSide: search.side === "right" ? "right" : "left",
    rightOrder: parseRightOrder(search.order),
    mapMaxWidth: numberFromQuery(search.map, 460, 280, 620),
    layoutGap: numberFromQuery(search.gap, 16, 8, 36),
    panelPadding: numberFromQuery(search.pad, 16, 8, 28),
    leftMinPx: numberFromQuery(search.lmin, 280, 220, 480),
    leftFr: numberFromQuery(search.lfr, 0.62, 0.35, 1.25),
    rightFr: numberFromQuery(search.rfr, 1.38, 0.9, 2.2),
    barHeight: numberFromQuery(search.barh, 320, 220, 520),
    lineHeight: numberFromQuery(search.lineh, 340, 240, 580),
  }
}
