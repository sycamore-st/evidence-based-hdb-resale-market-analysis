import Link from "next/link"

import { ValuationWorkbench } from "@/components/section2/valuation-workbench"

export default function QuestionBExtendedToolPage() {
  return (
    <main className="valuation-page">
      <section className="valuation-shell">
        <header className="valuation-header">
          <p>Section 2 / Question B / Extended Tool</p>
          <h1>Interactive Valuation Workbench</h1>
          <p>
            Choose transaction details, generate an expected valuation, and inspect local distribution plus comparable candidates.
          </p>
          <div className="valuation-links">
            <Link href="/section2/question-b">Open Question B writeup</Link>
            <Link href="/section2/question-b-extended">Open extended note</Link>
          </div>
        </header>

        <ValuationWorkbench />
      </section>
    </main>
  )
}

