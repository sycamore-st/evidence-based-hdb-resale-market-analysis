"use client"

import createPlotlyComponent from "react-plotly.js/factory"
import Plotly from "plotly.js-basic-dist-min"
import type { ComponentType, CSSProperties } from "react"

type PlotProps = {
  data?: unknown[]
  layout?: Record<string, unknown>
  config?: Record<string, unknown>
  className?: string
  style?: CSSProperties
  useResizeHandler?: boolean
}

const Plot = createPlotlyComponent(Plotly as never) as ComponentType<PlotProps>

export default Plot
