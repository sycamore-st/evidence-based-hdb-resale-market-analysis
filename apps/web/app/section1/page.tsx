import { SectionLanding } from "@/components/content/section-landing"
import { getSectionLandingItems } from "@/lib/sections"

export const dynamic = "force-static"

export default function Section1Page() {
  return (
    <SectionLanding
      section="section1"
      title="Explore the market yourself."
      description="Three interactive dashboards for browsing prices, comparing budgets, and shortlisting buildings across Singapore."
      items={getSectionLandingItems("section1")}
    />
  )
}
