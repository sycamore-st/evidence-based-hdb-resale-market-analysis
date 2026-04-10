import { notFound } from "next/navigation"

import { ArticleVariantC } from "@/components/content/article-variant-c"
import { getSiblingArticles, listSectionArticles, readArticle } from "@/lib/content"

export const dynamic = "force-static"
export const dynamicParams = false

export function generateStaticParams() {
  return listSectionArticles("section3").map((article) => ({ slug: article.slug }))
}

export default async function Section3ArticlePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const known = listSectionArticles("section3").some((article) => article.slug === slug)

  if (!known) {
    notFound()
  }

  const article = await readArticle("section3", slug)
  const siblings = getSiblingArticles("section3", slug)

  return <ArticleVariantC article={article} section="section3" previous={siblings.previous} next={siblings.next} />
}
