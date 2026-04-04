import { SectionLanding } from "@/components/content/section-landing"
import { listSectionArticles } from "@/lib/content"

export default function Section3Page() {
  return (
    <SectionLanding
      section="section3"
      title="Policy and town-level case writeups for Section 3."
      description="Structured markdown pages for the Section 3 questions, designed as readable web articles with linked figures and outputs."
      articles={listSectionArticles("section3")}
    />
  )
}
