"use client"

import Link from "next/link"

export const SECTION1_FLAT_COLORS: Record<string, string> = {
  "1 ROOM": "#8f9eaa",
  "2 ROOM": "#bfcfd7",
  "3 ROOM": "#b59995",
  "4 ROOM": "#d9c7aa",
  "5 ROOM": "#adbdad",
  EXECUTIVE: "#8b8fab",
  "MULTI-GENERATION": "#a58aa3",
}

export const SECTION1_CONTROL_LABELS = {
  transactionYear: "Select transaction year",
  flatType: "Select flat type",
  town: "Town",
  budget: "Budget",
  nearestMrtDistance: "Nearest MRT distance",
  nearestSchoolWithin1Km: "Nearest school within 1km",
  schoolCountWithin1Km: "School count within 1km",
  medianFloorArea: "Median floor area",
  selectedBuilding: "Selected building",
} as const

export function formatSectionCurrency(value: number): string {
  return new Intl.NumberFormat("en-SG", {
    style: "currency",
    currency: "SGD",
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatSectionCount(value: number): string {
  return new Intl.NumberFormat("en-SG").format(value)
}

const DASHBOARD_PAGES = [
  { href: "/section1/dashboard-1", title: "Town-level overview" },
  { href: "/section1/dashboard-2", title: "Buyer budget planner" },
  { href: "/section1/dashboard-3", title: "Find flats by budget and location" },
] as const

export function DashboardPager({ current }: { current: string }) {
  const index = DASHBOARD_PAGES.findIndex((page) => page.href === current)
  const previous = index > 0 ? DASHBOARD_PAGES[index - 1] : null
  const next = index < DASHBOARD_PAGES.length - 1 ? DASHBOARD_PAGES[index + 1] : null

  return (
    <div className="article-pager">
      {previous ? (
        <Link href={previous.href} className="article-pager-link">
          <small>Previous</small>
          <strong>{previous.title}</strong>
        </Link>
      ) : (
        <div />
      )}
      {next ? (
        <Link href={next.href} className="article-pager-link article-pager-link-next">
          <small>Next</small>
          <strong>{next.title}</strong>
        </Link>
      ) : null}
    </div>
  )
}

export function SectionDashboardNav({
  className,
}: {
  className: string
}) {
  return (
    <div className={`${className} site-topnav`}>
      <div className="site-topnav-links">
        <Link href="/section1" className="site-topnav-link">
          Section 1
        </Link>
        <Link href="/section2" className="site-topnav-link">
          Section 2
        </Link>
        <Link href="/section3" className="site-topnav-link">
          Section 3
        </Link>
      </div>
      <Link href="/#menu" className="site-topnav-action">
        Menu
      </Link>
    </div>
  )
}
