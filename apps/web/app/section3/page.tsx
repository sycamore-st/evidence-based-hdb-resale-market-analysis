import { SectionLanding } from "@/components/content/section-landing"
import { listArticleLandingItems } from "@/lib/content"

export default function Section3Page() {
  return (
    <SectionLanding
      section="section3"
      title="Policy and town-level case writeups for Section 3."
      description="Town comparisons, market structure questions, and policy-facing analyses presented as narrative case notes."
      items={listArticleLandingItems("section3")}
    />
  )
}
