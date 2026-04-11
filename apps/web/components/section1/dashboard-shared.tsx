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
