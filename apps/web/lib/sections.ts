import type { Route } from "next"

export type SiteSection = "section1" | "section2" | "section3"

export interface SectionLandingItem {
  slug: string
  title: string
  kicker: string
  description: string
  href: Route
  ctaLabel: string
}

export interface SectionShowcase {
  section: SiteSection
  title: string
  eyebrow: string
  description: string
  href: Route
  previewSrc: string
  previewAlt: string
  cardLabel: string
  ctaLabel: string
}

export interface MenuPageCard {
  label: string
  href: Route
  pageTitle: string
  description: string
}

export interface MenuPageRow {
  section: SiteSection
  title: string
  cards: MenuPageCard[]
}

export const SECTION_SHOWCASES: SectionShowcase[] = [
  {
    section: "section1",
    title: "Interactive dashboards",
    eyebrow: "Section 1",
    description:
      "Explore market movement, budget-to-space tradeoffs, and building-level shortlist tools through the browser dashboards.",
    href: "/section1",
    previewSrc: "/section-previews/section1-dashboard1-country-view.png",
    previewAlt: "Preview of the Section 1 country dashboard showing Singapore resale market activity.",
    cardLabel: "Dashboard suite",
    ctaLabel: "Open Section 1",
  },
  {
    section: "section2",
    title: "Predictive case writeups",
    eyebrow: "Section 2",
    description:
      "Read the model-driven valuation, prediction, and hidden-feature recovery cases with supporting charts and narrative.",
    href: "/section2",
    previewSrc: "/section-previews/section2-model-tradeoff.svg",
    previewAlt: "Preview of the Section 2 model tradeoff chart comparing predictive approaches.",
    cardLabel: "Case writeups",
    ctaLabel: "Open Section 2",
  },
  {
    section: "section3",
    title: "Policy and town-level analysis",
    eyebrow: "Section 3",
    description:
      "Review town comparisons, transport impact, flat-size trends, and policy-oriented market interpretation.",
    href: "/section3",
    previewSrc: "/section-previews/section3-yishun-coefficients.png",
    previewAlt: "Preview of the Section 3 controlled coefficient chart for the Yishun case study.",
    cardLabel: "Policy notes",
    ctaLabel: "Open Section 3",
  },
]

export const MENU_PAGE_ROWS: MenuPageRow[] = [
  {
    section: "section1",
    title: "Section 1",
    cards: [
      {
        label: "Dashboard 1",
        href: "/section1/dashboard-1",
        pageTitle: "Market overview",
        description: "Country and town views for transaction volume, pricing, and linked spatial market differences.",
      },
      {
        label: "Dashboard 2",
        href: "/section1/dashboard-2",
        pageTitle: "Budget to space",
        description: "Compare how much floor area different budgets can buy across towns and flat types.",
      },
      {
        label: "Dashboard 3",
        href: "/section1/dashboard-3",
        pageTitle: "Location optimizer",
        description: "Shortlist buildings by budget, transport access, schools, and nearby amenity context.",
      },
    ],
  },
  {
    section: "section2",
    title: "Section 2",
    cards: [
      {
        label: "Question A",
        href: "/section2/question-a" as Route,
        pageTitle: "Price prediction with restricted fields",
        description: "Estimate resale prices using only the visible case fields and compare model tradeoffs.",
      },
      {
        label: "Question B",
        href: "/section2/question-b" as Route,
        pageTitle: "Target transaction valuation",
        description: "Assess whether a subject Yishun resale transaction is materially overpriced versus expectation.",
      },
      {
        label: "Question C",
        href: "/section2/question-c" as Route,
        pageTitle: "Recover missing flat type",
        description: "Compare supervised and unsupervised recovery paths for flat type without losing pricing quality.",
      },
    ],
  },
  {
    section: "section3",
    title: "Section 3",
    cards: [
      {
        label: "Question A",
        href: "/section3/question-a" as Route,
        pageTitle: "Is Yishun truly cheaper?",
        description: "Test whether Yishun remains a value town after controlling for flat mix and timing effects.",
      },
      {
        label: "Question B",
        href: "/section3/question-b" as Route,
        pageTitle: "Are newer flats becoming smaller?",
        description: "Separate true shrinkage from town and flat-type composition shifts with controlled trend views.",
      },
      {
        label: "Question C",
        href: "/section3/question-c" as Route,
        pageTitle: "Did DTL2 lift nearby prices?",
        description: "Review the corridor-level treatment effect around Downtown Line Stage 2 station access.",
      },
      {
        label: "Question D",
        href: "/section3/question-d" as Route,
        pageTitle: "Do outer towns react more to COE?",
        description: "Compare far-town and central-town sensitivity to COE shocks through adjusted market indices.",
      },
    ],
  },
]

const SECTION1_LANDING_ITEMS: SectionLandingItem[] = [
  {
    slug: "dashboard-1",
    title: "Where are prices moving?",
    kicker: "Market overview",
    description: "Browse prices and transaction volumes by town and flat type across Singapore's resale market.",
    href: "/section1/dashboard-1",
    ctaLabel: "Open dashboard",
  },
  {
    slug: "dashboard-2",
    title: "What does your budget buy?",
    kicker: "Budget explorer",
    description: "See how much floor area you can get for your money — and how that varies by town and flat type.",
    href: "/section1/dashboard-2",
    ctaLabel: "Open dashboard",
  },
  {
    slug: "dashboard-3",
    title: "Find the right building",
    kicker: "Location search",
    description: "Shortlist buildings by budget, MRT access, schools, and nearby amenities to narrow down your options.",
    href: "/section1/dashboard-3",
    ctaLabel: "Open dashboard",
  },
]

export function getSectionLandingItems(section: SiteSection): SectionLandingItem[] {
  if (section === "section1") {
    return SECTION1_LANDING_ITEMS
  }
  return []
}

export function getSectionLabel(section: SiteSection): string {
  return section === "section1" ? "Section 1" : section === "section2" ? "Section 2" : "Section 3"
}
