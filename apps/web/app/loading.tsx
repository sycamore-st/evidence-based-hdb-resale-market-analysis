export default function Loading() {
  return (
    <main className="route-loading" role="status" aria-live="polite" aria-busy="true">
      <div className="route-loading-card">
        <span className="route-loading-spinner" aria-hidden="true" />
        <p>Loading HDB Resale Market Analysis...</p>
      </div>
    </main>
  )
}
