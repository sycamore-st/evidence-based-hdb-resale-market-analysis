import { SectionLanding } from "@/components/content/section-landing"
import { listArticleLandingItems } from "@/lib/content"

export const dynamic = "force-static"

export default function Section2Page() {
  return (
    <SectionLanding
      section="section2"
      title="What can the data actually tell us?"
      description="Four deep dives into pricing accuracy, valuation fairness, and the limits of incomplete information."
      items={listArticleLandingItems("section2")}
    />
  )
}
