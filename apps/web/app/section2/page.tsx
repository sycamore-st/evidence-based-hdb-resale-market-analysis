import { SectionLanding } from "@/components/content/section-landing"
import { listSectionArticles } from "@/lib/content"

export default function Section2Page() {
  return (
    <SectionLanding
      section="section2"
      title="Predictive case writeups for Section 2."
      articles={listSectionArticles("section2")}
    />
  )
}
