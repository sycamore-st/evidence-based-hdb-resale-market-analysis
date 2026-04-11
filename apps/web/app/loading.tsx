export default function Loading() {
  return (
    <main className="route-loading" role="status" aria-live="polite" aria-busy="true">
      <div className="route-loading-card">
        <div className="route-loading-dots">
          <span className="route-loading-dot" />
          <span className="route-loading-dot" />
          <span className="route-loading-dot" />
        </div>
        <p>Loading…</p>
      </div>
    </main>
  )
}
