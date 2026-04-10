import type { Metadata } from "next"
import type { ReactNode } from "react"

import "@/app/globals.css"
import "@/app/katex.css"

export const metadata: Metadata = {
  title: "Evidence-Based HDB Resale Market Analysis",
  description: "Interactive web dashboards for the evidence-based HDB resale market analysis project.",
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
