declare module "react-plotly.js/factory" {
  const factory: (plotly: unknown) => unknown
  export default factory
}

declare module "plotly.js-basic-dist-min" {
  const plotly: unknown
  export default plotly
}

declare module "plotly.js/dist/plotly.min" {
  const plotly: typeof import("plotly.js")
  export default plotly
}
