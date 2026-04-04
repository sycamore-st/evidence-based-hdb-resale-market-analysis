import { notFound } from "next/navigation"

import { ArticleVariantC } from "@/components/content/article-variant-c"
import { getSiblingArticles, listSectionArticles, readArticle } from "@/lib/content"

export function generateStaticParams() {
  return listSectionArticles("section2").map((article) => ({ slug: article.slug }))
}

export default async function Section2ArticlePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const known = listSectionArticles("section2").some((article) => article.slug === slug)

  if (!known) {
    notFound()
  }

  const article = await readArticle("section2", slug)
  const siblings = getSiblingArticles("section2", slug)

  return <ArticleVariantC article={article} section="section2" previous={siblings.previous} next={siblings.next} />
}
