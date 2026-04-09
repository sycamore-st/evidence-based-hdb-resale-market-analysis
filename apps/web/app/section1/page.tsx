import { SectionLanding } from "@/components/content/section-landing"
import { getSectionLandingItems } from "@/lib/sections"

export default function Section1Page() {
  return (
    <SectionLanding
      section="section1"
      title="Interactive dashboards for market exploration."
      description="Move between the three browser dashboards for market overview, buyer budget tradeoffs, and building-level location search."
      items={getSectionLandingItems("section1")}
    />
  )
}
