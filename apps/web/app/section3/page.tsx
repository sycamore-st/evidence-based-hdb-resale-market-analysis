import { SectionLanding } from "@/components/content/section-landing"
import { listArticleLandingItems } from "@/lib/content"

export const dynamic = "force-static"

export default function Section3Page() {
  return (
    <SectionLanding
      section="section3"
      title="Stories behind the numbers."
      description="Town rivalries, shrinking flats, new train lines, and the ripple effects of policy — examined one question at a time."
      items={listArticleLandingItems("section3")}
    />
  )
}
