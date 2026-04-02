"use client"

import Link from "next/link"
import { useEffect, useMemo, useState } from "react"

import { DashboardOneExplorer, type DashboardOneLayoutPreset, type DashboardOneStyleVars } from "@/components/section1/dashboard-one-explorer"
import type { DashboardOneData } from "@/lib/section1-dashboard1"
import type {
  DashboardOneMapSide,
  DashboardOneRightPanel,
  DashboardOneSandboxState as SandboxState,
} from "@/lib/section1-dashboard1-sandbox"

const RIGHT_PANEL_OPTIONS: DashboardOneRightPanel[] = ["legend", "bars", "lines"]

export function DashboardOneSandbox({
  data,
  initial,
}: {
  data: DashboardOneData
  initial: SandboxState
}) {
  const [state, setState] = useState<SandboxState>(initial)

  const styleVars = useMemo<DashboardOneStyleVars>(
    () => ({
      "--d1-map-max-width": `${state.mapMaxWidth}px`,
      "--d1-layout-gap": `${state.layoutGap}px`,
      "--d1-panel-padding": `${state.panelPadding}px`,
      "--d1-left-col-min": `${state.leftMinPx}px`,
      "--d1-left-col-fr": `${state.leftFr}fr`,
      "--d1-right-col-fr": `${state.rightFr}fr`,
      "--d1-bar-height": `${state.barHeight}px`,
      "--d1-line-height": `${state.lineHeight}px`,
    }),
    [state],
  )

  const tokenSnippet = useMemo(
    () =>
      `:root {\n` +
      `  --d1-map-max-width: ${state.mapMaxWidth}px;\n` +
      `  --d1-layout-gap: ${state.layoutGap}px;\n` +
      `  --d1-panel-padding: ${state.panelPadding}px;\n` +
      `  --d1-left-col-min: ${state.leftMinPx}px;\n` +
      `  --d1-left-col-fr: ${state.leftFr}fr;\n` +
      `  --d1-right-col-fr: ${state.rightFr}fr;\n` +
      `  --d1-bar-height: ${state.barHeight}px;\n` +
      `  --d1-line-height: ${state.lineHeight}px;\n` +
      `}`,
    [state],
  )

  useEffect(() => {
    const params = new URLSearchParams()
    params.set("layout", state.layout)
    params.set("side", state.mapSide)
    params.set("order", state.rightOrder.join(","))
    params.set("map", String(state.mapMaxWidth))
    params.set("gap", String(state.layoutGap))
    params.set("pad", String(state.panelPadding))
    params.set("lmin", String(state.leftMinPx))
    params.set("lfr", String(state.leftFr))
    params.set("rfr", String(state.rightFr))
    params.set("barh", String(state.barHeight))
    params.set("lineh", String(state.lineHeight))
    if (typeof window !== "undefined") {
      const nextUrl = `${window.location.pathname}?${params.toString()}`
      window.history.replaceState({}, "", nextUrl)
    }
  }, [state])

  const update = <K extends keyof SandboxState>(key: K, value: SandboxState[K]) => {
    setState((previous) => ({ ...previous, [key]: value }))
  }

  const updateRightOrder = (slotIndex: number, panel: DashboardOneRightPanel) => {
    setState((previous) => {
      const nextOrder = [...previous.rightOrder]
      const existingIndex = nextOrder.indexOf(panel)
      const currentAtSlot = nextOrder[slotIndex]
      if (existingIndex >= 0 && existingIndex !== slotIndex) {
        nextOrder[existingIndex] = currentAtSlot
      }
      nextOrder[slotIndex] = panel
      return { ...previous, rightOrder: nextOrder }
    })
  }

  return (
    <div className="dashboard1-sandbox-wrap">
      <aside className="dashboard1-sandbox-panel">
        <div className="dashboard1-sandbox-header">
          <p>Layout Sandbox</p>
          <Link href="/section1/dashboard-1">open normal page</Link>
        </div>

        <label>
          <span>Preset</span>
          <select value={state.layout} onChange={(event) => update("layout", event.target.value as DashboardOneLayoutPreset)}>
            <option value="editorial">editorial</option>
            <option value="balanced">balanced</option>
            <option value="chart-heavy">chart-heavy</option>
          </select>
        </label>

        <label>
          <span>Map side</span>
          <select value={state.mapSide} onChange={(event) => update("mapSide", event.target.value as DashboardOneMapSide)}>
            <option value="left">left</option>
            <option value="right">right</option>
          </select>
        </label>

        <label>
          <span>Right column top card</span>
          <select value={state.rightOrder[0]} onChange={(event) => updateRightOrder(0, event.target.value as DashboardOneRightPanel)}>
            {RIGHT_PANEL_OPTIONS.map((option) => (
              <option key={`top-${option}`} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Right column middle card</span>
          <select value={state.rightOrder[1]} onChange={(event) => updateRightOrder(1, event.target.value as DashboardOneRightPanel)}>
            {RIGHT_PANEL_OPTIONS.map((option) => (
              <option key={`middle-${option}`} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Right column bottom card</span>
          <select value={state.rightOrder[2]} onChange={(event) => updateRightOrder(2, event.target.value as DashboardOneRightPanel)}>
            {RIGHT_PANEL_OPTIONS.map((option) => (
              <option key={`bottom-${option}`} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Map max width ({state.mapMaxWidth}px)</span>
          <input type="range" min={280} max={620} step={10} value={state.mapMaxWidth} onChange={(event) => update("mapMaxWidth", Number(event.target.value))} />
        </label>

        <label>
          <span>Layout gap ({state.layoutGap}px)</span>
          <input type="range" min={8} max={36} step={1} value={state.layoutGap} onChange={(event) => update("layoutGap", Number(event.target.value))} />
        </label>

        <label>
          <span>Panel padding ({state.panelPadding}px)</span>
          <input type="range" min={8} max={28} step={1} value={state.panelPadding} onChange={(event) => update("panelPadding", Number(event.target.value))} />
        </label>

        <label>
          <span>Left column min ({state.leftMinPx}px)</span>
          <input type="range" min={220} max={480} step={10} value={state.leftMinPx} onChange={(event) => update("leftMinPx", Number(event.target.value))} />
        </label>

        <label>
          <span>Left column fr ({state.leftFr.toFixed(2)})</span>
          <input type="range" min={0.35} max={1.25} step={0.01} value={state.leftFr} onChange={(event) => update("leftFr", Number(event.target.value))} />
        </label>

        <label>
          <span>Right column fr ({state.rightFr.toFixed(2)})</span>
          <input type="range" min={0.9} max={2.2} step={0.01} value={state.rightFr} onChange={(event) => update("rightFr", Number(event.target.value))} />
        </label>

        <label>
          <span>Bar chart height ({state.barHeight}px)</span>
          <input type="range" min={220} max={520} step={10} value={state.barHeight} onChange={(event) => update("barHeight", Number(event.target.value))} />
        </label>

        <label>
          <span>Line chart height ({state.lineHeight}px)</span>
          <input type="range" min={240} max={580} step={10} value={state.lineHeight} onChange={(event) => update("lineHeight", Number(event.target.value))} />
        </label>

        <div className="dashboard1-sandbox-snippet">
          <p>Copy this token block</p>
          <pre>{tokenSnippet}</pre>
        </div>
      </aside>

      <div className="dashboard1-sandbox-canvas">
        <DashboardOneExplorer
          data={data}
          layoutPreset={state.layout}
          mapSide={state.mapSide}
          rightOrder={state.rightOrder}
          styleVars={styleVars}
          layoutLinkBase="/section1/dashboard-1/sandbox"
        />
      </div>
    </div>
  )
}
