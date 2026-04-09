"use client"

import { useEffect, useMemo, useState } from "react"

import Plot from "@/components/charts/plotly-chart"

type ValuationOptions = {
  scope: string
  flatModels: string[]
  months: string[]
  buildings: Array<{
    buildingKey: string
    block: string
    streetName: string
    label: string
  }>
  defaults: {
    transactionMonth: string
    buildingKey: string
    floorAreaSqm: number
    leaseCommenceDate: number
    minFloorLevel: number
    maxFloorLevel: number
    flatModel: string
    actualPrice: number
  }
}

type ValuationResult = {
  scope: string
  metrics: {
    expectedPrice: number
    modelEstimate: number
    comparablesEstimate: number | null
    intervalLow: number
    intervalHigh: number
    localP025: number
    localP25: number
    localP50: number
    localP75: number
    localP975: number
    comparablesCount: number
    localCount: number
  }
  decision: {
    confidence: "High" | "Moderate" | "Limited"
    verdict: "Likely Overpriced" | "Likely Underpriced" | "Within Expected Range" | "Insufficient Price Input"
    deviationPct: number | null
    deviationAmount: number | null
    note: string
  }
  comparables: Array<{
    id: string
    buildingKey: string
    block: string
    streetName: string
    transactionMonth: string
    flatModel: string
    floorAreaSqm: number
    resalePrice: number
    adjustedPrice: number
    geoDistanceKm: number
    areaGapSqm: number
    ageGapYears: number
    score: number
  }>
  chartData: {
    histogramPrices: number[]
    comparableArea: number[]
    comparablePrice: number[]
    comparableLabels: string[]
  }
}

type FormState = {
  transactionMonth: string
  buildingKey: string
  floorAreaSqm: number
  leaseCommenceDate: number
  minFloorLevel: number
  maxFloorLevel: number
  flatModel: string
  actualPrice: string
}

function formatCurrency(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "N/A"
  }
  return new Intl.NumberFormat("en-SG", {
    style: "currency",
    currency: "SGD",
    maximumFractionDigits: 0,
  }).format(value)
}

function formatPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "N/A"
  }
  return `${(value * 100).toFixed(1)}%`
}

export function ValuationWorkbench() {
  const [options, setOptions] = useState<ValuationOptions | null>(null)
  const [result, setResult] = useState<ValuationResult | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState<FormState | null>(null)

  useEffect(() => {
    let active = true

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const response = await fetch("/api/section2/valuation", { cache: "no-store" })
        if (!response.ok) {
          throw new Error(`Failed to load options (${response.status})`)
        }
        const payload = (await response.json()) as ValuationOptions
        if (!active) {
          return
        }
        setOptions(payload)
        setForm({
          transactionMonth: payload.defaults.transactionMonth,
          buildingKey: payload.defaults.buildingKey,
          floorAreaSqm: payload.defaults.floorAreaSqm,
          leaseCommenceDate: payload.defaults.leaseCommenceDate,
          minFloorLevel: payload.defaults.minFloorLevel,
          maxFloorLevel: payload.defaults.maxFloorLevel,
          flatModel: payload.defaults.flatModel,
          actualPrice: String(payload.defaults.actualPrice),
        })
      } catch (requestError) {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load options.")
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void load()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!form) {
      return
    }

    let active = true
    const timeout = setTimeout(() => {
      void (async () => {
        setError(null)
        try {
          const response = await fetch("/api/section2/valuation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ...form,
              actualPrice: form.actualPrice.trim().length > 0 ? Number(form.actualPrice) : null,
            }),
          })
          if (!response.ok) {
            const payload = (await response.json()) as { error?: string }
            throw new Error(payload.error ?? `Failed to evaluate (${response.status})`)
          }
          const payload = (await response.json()) as ValuationResult
          if (active) {
            setResult(payload)
          }
        } catch (requestError) {
          if (active) {
            setError(requestError instanceof Error ? requestError.message : "Unable to evaluate this transaction.")
          }
        }
      })()
    }, 250)

    return () => {
      active = false
      clearTimeout(timeout)
    }
  }, [form])

  const distributionLayout = useMemo(
    () => ({
      margin: { l: 52, r: 20, t: 18, b: 54 },
      bargap: 0.12,
      xaxis: {
        title: "Resale Price (SGD)",
        showgrid: false,
        zeroline: false,
      },
      yaxis: {
        title: "Count",
        showgrid: false,
        zeroline: false,
      },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: '"Avenir Next", "Segoe UI", sans-serif', size: 12, color: "rgba(46, 42, 35, 0.88)" },
    }),
    []
  )

  const comparablesLayout = useMemo(
    () => ({
      margin: { l: 52, r: 20, t: 18, b: 54 },
      xaxis: {
        title: "Price per sqft (SGD)",
        showgrid: false,
        zeroline: false,
      },
      yaxis: {
        title: "Transaction Price (SGD)",
        showgrid: false,
        zeroline: false,
      },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: '"Avenir Next", "Segoe UI", sans-serif', size: 12, color: "rgba(46, 42, 35, 0.88)" },
    }),
    []
  )

  if (loading && !options) {
    return <p className="valuation-loading">Loading valuation workbench...</p>
  }

  if (error && !options) {
    return <p className="valuation-error">{error}</p>
  }

  if (!options || !form) {
    return <p className="valuation-error">Options are unavailable.</p>
  }

  return (
    <div className="valuation-workbench">
      <p className="valuation-scope">{options.scope}</p>

      <section className="valuation-input-grid">
        <label>
          <span>Transaction Month</span>
          <select
            value={form.transactionMonth}
            onChange={(event) => setForm((current) => (current ? { ...current, transactionMonth: event.target.value } : current))}
          >
            {options.months.map((month) => (
              <option key={month} value={month}>
                {month}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Building</span>
          <select
            value={form.buildingKey}
            onChange={(event) => setForm((current) => (current ? { ...current, buildingKey: event.target.value } : current))}
          >
            {options.buildings.map((building) => (
              <option key={building.buildingKey} value={building.buildingKey}>
                {building.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Flat Model</span>
          <select
            value={form.flatModel}
            onChange={(event) => setForm((current) => (current ? { ...current, flatModel: event.target.value } : current))}
          >
            {options.flatModels.map((flatModel) => (
              <option key={flatModel} value={flatModel}>
                {flatModel}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Floor Area (sqm)</span>
          <input
            type="number"
            min={50}
            max={140}
            step={1}
            value={form.floorAreaSqm}
            onChange={(event) =>
              setForm((current) => (current ? { ...current, floorAreaSqm: Number(event.target.value) } : current))
            }
          />
        </label>

        <label>
          <span>Lease Commence Year</span>
          <input
            type="number"
            min={1970}
            max={2020}
            step={1}
            value={form.leaseCommenceDate}
            onChange={(event) =>
              setForm((current) => (current ? { ...current, leaseCommenceDate: Number(event.target.value) } : current))
            }
          />
        </label>

        <label>
          <span>Min Floor Level</span>
          <input
            type="number"
            min={1}
            max={50}
            step={1}
            value={form.minFloorLevel}
            onChange={(event) =>
              setForm((current) => (current ? { ...current, minFloorLevel: Number(event.target.value) } : current))
            }
          />
        </label>

        <label>
          <span>Max Floor Level</span>
          <input
            type="number"
            min={1}
            max={60}
            step={1}
            value={form.maxFloorLevel}
            onChange={(event) =>
              setForm((current) => (current ? { ...current, maxFloorLevel: Number(event.target.value) } : current))
            }
          />
        </label>

        <label>
          <span>Actual Transaction Price (optional)</span>
          <input
            type="number"
            min={100000}
            max={2000000}
            step={1000}
            value={form.actualPrice}
            onChange={(event) => setForm((current) => (current ? { ...current, actualPrice: event.target.value } : current))}
          />
        </label>
      </section>

      {error ? <p className="valuation-error">{error}</p> : null}

      {result ? (
        <>
          <section className="valuation-metric-grid">
            <article>
              <p>Expected Price</p>
              <h3>{formatCurrency(result.metrics.expectedPrice)}</h3>
              <small>
                Blend of model-style estimate ({formatCurrency(result.metrics.modelEstimate)}) and comparables (
                {formatCurrency(result.metrics.comparablesEstimate)})
              </small>
            </article>
            <article>
              <p>Expected Interval</p>
              <h3>
                {formatCurrency(result.metrics.intervalLow)} to {formatCurrency(result.metrics.intervalHigh)}
              </h3>
              <small>Local empirical 95% range proxy</small>
            </article>
            <article>
              <p>Decision</p>
              <h3>{result.decision.verdict}</h3>
              <small>
                Deviation {formatCurrency(result.decision.deviationAmount)} ({formatPercent(result.decision.deviationPct)}), confidence{" "}
                {result.decision.confidence}
              </small>
            </article>
          </section>

          <p className="valuation-note">{result.decision.note}</p>

          <section className="valuation-chart-grid">
            <article>
              <h3>Local Transaction Distribution</h3>
              <Plot
                data={[
                  {
                    type: "histogram",
                    x: result.chartData.histogramPrices,
                    marker: {
                      color: "rgba(201, 117, 47, 0.38)",
                      line: { color: "#c9752f", width: 1.2 },
                    },
                    nbinsx: 24,
                    name: "Local prices",
                  },
                ]}
                layout={distributionLayout}
                config={{ responsive: true, displayModeBar: false }}
                useResizeHandler
                style={{ width: "100%", height: 320 }}
              />
            </article>
            <article>
              <h3>Comparable Transactions</h3>
              <Plot
                data={[
                  {
                    type: "scatter",
                    mode: "markers",
                    x: result.comparables.map((item) => item.resalePrice / (item.floorAreaSqm * 10.7639)),
                    y: result.comparables.map((item) => item.resalePrice),
                    text: result.comparables.map(
                      (item) =>
                        `${item.block} ${item.streetName}<br>${item.transactionMonth}<br>${item.floorAreaSqm.toFixed(1)} sqm`
                    ),
                    marker: {
                      color: result.comparables.map((item) => item.floorAreaSqm),
                      colorscale: [
                        [0, "#d7c1a0"],
                        [0.5, "#c9752f"],
                        [1, "#4f6e8a"],
                      ],
                      colorbar: {
                        title: { text: "Floor area (sqm)" },
                      },
                      line: { color: "rgba(79, 110, 138, 0.55)", width: 0.9 },
                      size: 10,
                    },
                    name: "Comparables",
                    customdata: result.comparables.map((item) => [item.floorAreaSqm, item.adjustedPrice]),
                    hovertemplate:
                      "%{text}<br>PSF: SGD %{x:.0f}<br>Transaction Price: SGD %{y:,.0f}<br>Adjusted Price: SGD %{customdata[1]:,.0f}<extra></extra>",
                  },
                ]}
                layout={comparablesLayout}
                config={{ responsive: true, displayModeBar: false }}
                useResizeHandler
                style={{ width: "100%", height: 320 }}
              />
            </article>
          </section>

          <section className="valuation-comps">
            <h3>Top Comparable Candidates</h3>
            <p>
              {result.metrics.comparablesCount} retained comparables, local pool {result.metrics.localCount} records.
            </p>
            <div className="valuation-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Block / Street</th>
                    <th>Month</th>
                    <th>Model</th>
                    <th>Area</th>
                    <th>Price</th>
                    <th>Adj. Price</th>
                    <th>Geo Dist (km)</th>
                  </tr>
                </thead>
                <tbody>
                  {result.comparables.map((item) => (
                    <tr key={item.id}>
                      <td>
                        {item.block} {item.streetName}
                      </td>
                      <td>{item.transactionMonth}</td>
                      <td>{item.flatModel}</td>
                      <td>{item.floorAreaSqm.toFixed(1)}</td>
                      <td>{formatCurrency(item.resalePrice)}</td>
                      <td>{formatCurrency(item.adjustedPrice)}</td>
                      <td>{item.geoDistanceKm.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : (
        <p className="valuation-loading">Generating valuation...</p>
      )}
    </div>
  )
}
