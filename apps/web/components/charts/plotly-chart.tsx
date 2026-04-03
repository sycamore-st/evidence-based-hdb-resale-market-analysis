"use client"

import Plotly from "plotly.js/dist/plotly.min"
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

    Promise.resolve(Plotly.react(node, data as never, layout as never, config as never)).then(() => {
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

    return () => {
      cancelled = true
    }
  }, [config, data, layout, onClick, onHover, onUnhover])

  useEffect(() => {
    if (!useResizeHandler) return

    const handleResize = () => {
      if (containerRef.current) {
        void Plotly.Plots.resize(containerRef.current as never)
      }
    }

    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [useResizeHandler])

  useEffect(() => {
    return () => {
      if (containerRef.current) {
        containerRef.current.removeAllListeners?.()
        void Plotly.purge(containerRef.current as never)
      }
    }
  }, [])

  return <div ref={containerRef} className={className} style={style} />
}
