import type { ReactNode } from "react"

import { Sidebar } from "@/components/layout/sidebar"

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <div className="background-glow" />
      <Sidebar />
      <main className="page-shell">{children}</main>
    </div>
  )
}
