export const theme = {
  colors: {
    background: "oklch(0.98 0.01 95)",
    foreground: "oklch(0.15 0.01 260)",
    card: "oklch(0.995 0.005 95)",
    border: "oklch(0.9 0.01 95)",
    muted: "oklch(0.95 0.01 95)",
    primary: "#7ec8e3",
    accent: "#f8d9a0",
    overlay: "rgba(255, 255, 255, 0.30)"
  },
  sections: [
    { href: "/overview", label: "Overview" },
    { href: "/policy", label: "Policy" },
    { href: "/model", label: "Model" }
  ]
} as const

export type DashboardSection = "overview" | "policy" | "model"
