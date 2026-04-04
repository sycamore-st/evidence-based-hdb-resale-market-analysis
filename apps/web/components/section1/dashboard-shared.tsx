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
  transactionYear: "Transaction year",
  flatType: "Flat type",
  town: "Town",
  budget: "Budget",
  nearestMrtDistance: "Nearest MRT distance",
  nearestSchoolWithin1Km: "Nearest school within 1km",
  schoolCountWithin1Km: "School count within 1km",
  medianFloorArea: "Median floor area",
  selectedBuilding: "Selected building",
} as const

const DASHBOARD_ROUTES = [
  { key: "dashboard-1", href: "/section1/dashboard-1", label: "Dashboard 1" },
  { key: "dashboard-2", href: "/section1/dashboard-2", label: "Dashboard 2" },
  { key: "dashboard-3", href: "/section1/dashboard-3", label: "Dashboard 3" },
] as const

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

export function SectionDashboardNav({
  current,
  className,
}: {
  current: (typeof DASHBOARD_ROUTES)[number]["key"]
  className: string
}) {
  return (
    <div className={className}>
      {DASHBOARD_ROUTES.filter((item) => item.key !== current).map((item) => (
        <Link key={item.key} href={item.href} className="section1-nav-link">
          {item.label}
        </Link>
      ))}
      <Link href="/" className="section1-nav-link">
        Back to index
      </Link>
    </div>
  )
}
