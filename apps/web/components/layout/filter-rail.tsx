import type { DashboardFilters } from "@/lib/artifacts"

export function FilterRail({ filters }: { filters: DashboardFilters }) {
  return (
    <aside className="filter-rail">
      <div className="filter-header">
        <p className="eyebrow">Available filters</p>
        <span>Frontend reads published options only.</span>
      </div>
      <div className="filter-groups">
        {filters.filters.map((filter) => (
          <section key={filter.id} className="filter-group">
            <h3>{filter.label}</h3>
            <div className="chip-list">
              {filter.options.map((option) => (
                <span key={option} className="chip">
                  {option}
                </span>
              ))}
            </div>
          </section>
        ))}
      </div>
    </aside>
  )
}
