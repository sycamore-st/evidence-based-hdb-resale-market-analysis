"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

import { theme } from "@/lib/theme"

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <p className="eyebrow">Evidence-Based</p>
        <h1>HDB Resale</h1>
        <span>Dashboard workspace</span>
      </div>
      <nav className="sidebar-nav" aria-label="Dashboard sections">
        {theme.sections.map((section) => {
          const isActive = pathname === section.href
          return (
            <Link
              key={section.href}
              href={section.href}
              className={isActive ? "nav-link nav-link-active" : "nav-link"}
            >
              {section.label}
            </Link>
          )
        })}
      </nav>
      <div className="sidebar-note">
        <p>Precomputed artifacts</p>
        <span>Built from Python pipelines and served as stable JSON payloads.</span>
      </div>
    </aside>
  )
}
