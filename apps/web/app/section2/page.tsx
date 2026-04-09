import { SectionLanding } from "@/components/content/section-landing"
import { listArticleLandingItems } from "@/lib/content"

export default function Section2Page() {
  return (
    <SectionLanding
      section="section2"
      title="Predictive case writeups for Section 2."
      description="Model evaluation, valuation logic, and hidden-feature recovery writeups with supporting charts and discussion."
      items={listArticleLandingItems("section2")}
    />
  )
}
