import type { Metadata } from "next"
import type { ReactNode } from "react"

import "@/app/globals.css"

export const metadata: Metadata = {
  title: "Evidence-Based HDB Resale Dashboard",
  description: "Frontend scaffold for overview, policy, and modeling dashboards."
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
