"use client"

import { useEffect, useRef } from "react"
import type { CSSProperties } from "react"

type PlotProps = {
  data?: unknown[]
  layout?: Record<string, unknown>
  config?: Record<string, unknown>
  className?: string
  style?: CSSProperties
  useResizeHandler?: boolean
  onHover?: (event: unknown) => void
  onUnhover?: (event: unknown) => void
  onClick?: (event: unknown) => void
}

type PlotlyGraphDiv = HTMLDivElement & {
  on?: (eventName: string, handler: (event: unknown) => void) => void
  removeAllListeners?: (eventName?: string) => void
}

type PlotlyModule = {
  react: (element: unknown, data: unknown, layout: unknown, config: unknown) => Promise<unknown> | unknown
  purge: (element: unknown) => Promise<unknown> | unknown
  Plots: {
    resize: (element: unknown) => Promise<unknown> | unknown
  }
}

let plotlyPromise: Promise<PlotlyModule> | null = null

function loadPlotly(): Promise<PlotlyModule> {
  if (!plotlyPromise) {
    plotlyPromise = import("plotly.js/dist/plotly.min").then((module) => module.default as unknown as PlotlyModule)
  }
  return plotlyPromise
}

export default function Plot({
  data = [],
  layout = {},
  config = {},
  className,
  style,
  useResizeHandler = false,
  onHover,
  onUnhover,
  onClick,
}: PlotProps) {
  const containerRef = useRef<PlotlyGraphDiv | null>(null)

  useEffect(() => {
    const node = containerRef.current
    if (!node) return

    let cancelled = false

    void loadPlotly().then((plotly) =>
      Promise.resolve(plotly.react(node, data as never, layout as never, config as never)).then(() => {
        if (cancelled || !node) return

        node.removeAllListeners?.("plotly_hover")
        node.removeAllListeners?.("plotly_unhover")
        node.removeAllListeners?.("plotly_click")

        if (onHover) {
          node.on?.("plotly_hover", onHover)
        }
        if (onUnhover) {
          node.on?.("plotly_unhover", onUnhover)
        }
        if (onClick) {
          node.on?.("plotly_click", onClick)
        }
      })
    )

    return () => {
      cancelled = true
    }
  }, [config, data, layout, onClick, onHover, onUnhover])

  useEffect(() => {
    if (!useResizeHandler) return

    const handleResize = () => {
      if (containerRef.current) {
        void loadPlotly().then((plotly) => plotly.Plots.resize(containerRef.current as never))
      }
    }

    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [useResizeHandler])

  useEffect(() => {
    return () => {
      if (containerRef.current) {
        const node = containerRef.current
        node.removeAllListeners?.()
        void loadPlotly().then((plotly) => plotly.purge(node as never))
      }
    }
  }, [])

  return <div ref={containerRef} className={className} style={style} />
}
