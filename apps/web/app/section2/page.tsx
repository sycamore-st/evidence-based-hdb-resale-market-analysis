import { SectionLanding } from "@/components/content/section-landing"
import { listSectionArticles } from "@/lib/content"

export default function Section2Page() {
  return (
    <SectionLanding
      section="section2"
      title="Predictive case writeups for Section 2."
      description="Markdown-driven analysis pages that turn the Section 2 case notes into a cleaner web reading experience."
      articles={listSectionArticles("section2")}
    />
  )
}
