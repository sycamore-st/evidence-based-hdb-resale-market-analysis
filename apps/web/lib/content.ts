import type { Route } from "next"
import { readFile } from "node:fs/promises"
import path from "node:path"

import matter from "gray-matter"

import { resolveMarkdownUrl } from "@/lib/markdown-url"
import type { SectionLandingItem } from "@/lib/sections"

export type ArticleSection = "section2" | "section3"

export interface ArticleFrontmatter {
  title?: string
  kicker?: string
  description?: string
  section?: ArticleSection
  slug?: string
  order?: number
}

export interface ArticleMeta {
  section: ArticleSection
  slug: string
  title: string
  kicker: string
  description: string
  order: number
  readingLabel: string
}

export interface ArticleDocument {
  meta: ArticleMeta
  body: string
}

const CONTENT_ROOT = path.join(process.cwd(), "content")

const ARTICLE_REGISTRY: Record<ArticleSection, ArticleMeta[]> = {
  section2: [
    {
      section: "section2",
      slug: "question-a",
      title: "Question A: Price prediction with restricted visible fields",
      kicker: "Section 2 / Question A",
      description: "How accurately can resale price be predicted when only the visible case fields are allowed?",
      order: 1,
      readingLabel: "Prediction under limited inputs",
    },
    {
      section: "section2",
      slug: "question-b",
      title: "Question B: Is the target transaction overpriced?",
      kicker: "Section 2 / Question B",
      description: "A valuation note combining expected-price modeling, local context, and outlier checks.",
      order: 2,
      readingLabel: "Valuation and comparable context",
    },
    {
      section: "section2",
      slug: "question-c",
      title: "Question C: Can hidden flat type be recovered reliably?",
      kicker: "Section 2 / Question C",
      description: "A classification and clustering study on whether flat-type recovery preserves downstream pricing quality.",
      order: 4,
      readingLabel: "Recovery of hidden categories",
    },
    {
      section: "section2",
      slug: "question-b-extended",
      title: "Question B Extended: Interactive Valuation Workbench",
      kicker: "Section 2 / Question B (Extended)",
      description: "An interactive valuation sandbox for transaction-level expected price, local distribution, and comparables.",
      order: 3,
      readingLabel: "Interactive valuation workflow",
    },
  ],
  section3: [
    {
      section: "section3",
      slug: "question-a",
      title: "Question A: Is Yishun genuinely a value town?",
      kicker: "Section 3 / Question A",
      description: "A controlled town comparison to test whether Yishun remains cheaper after accounting for flat characteristics.",
      order: 1,
      readingLabel: "Town-level value comparison",
    },
    {
      section: "section3",
      slug: "question-b",
      title: "Question B: Are flats getting smaller over time?",
      kicker: "Section 3 / Question B",
      description: "A decomposition of transaction mix effects versus within-flat-type floor-area changes.",
      order: 2,
      readingLabel: "Space trends and composition effects",
    },
    {
      section: "section3",
      slug: "question-c",
      title: "Question C: Did Downtown Line Stage 2 shift nearby prices?",
      kicker: "Section 3 / Question C",
      description: "A treatment-versus-comparison design for transit access and resale price change.",
      order: 3,
      readingLabel: "Transit and pricing impact",
    },
    {
      section: "section3",
      slug: "question-d",
      title: "Question D: Are outer towns more sensitive to COE?",
      kicker: "Section 3 / Question D",
      description: "A relative-sensitivity study comparing how central and outer towns react after controls.",
      order: 4,
      readingLabel: "Macro sensitivity by town type",
    },
  ],
}

function getContentPath(section: ArticleSection, slug: string): string {
  return path.join(CONTENT_ROOT, section, `${slug}.md`)
}

function getRegistryMeta(section: ArticleSection, slug: string): ArticleMeta {
  const meta = ARTICLE_REGISTRY[section].find((item) => item.slug === slug)
  if (!meta) {
    throw new Error(`Unknown article ${section}/${slug}`)
  }
  return meta
}

function normalizeMeta(
  section: ArticleSection,
  slug: string,
  frontmatter: ArticleFrontmatter,
  fallback: ArticleMeta
): ArticleMeta {
  return {
    section,
    slug,
    title: frontmatter.title ?? fallback.title,
    kicker: frontmatter.kicker ?? fallback.kicker,
    description: frontmatter.description ?? fallback.description,
    order: frontmatter.order ?? fallback.order,
    readingLabel: fallback.readingLabel,
  }
}

export function listSectionArticles(section: ArticleSection): ArticleMeta[] {
  return [...ARTICLE_REGISTRY[section]].sort((left, right) => left.order - right.order)
}

export function listArticleLandingItems(section: ArticleSection): SectionLandingItem[] {
  return listSectionArticles(section).map((article) => ({
    slug: article.slug,
    title: article.title,
    kicker: article.kicker,
    description: article.description,
    href: `/${section}/${article.slug}` as Route,
    ctaLabel: "Read article",
  }))
}

export async function readArticle(section: ArticleSection, slug: string): Promise<ArticleDocument> {
  const raw = await readFile(getContentPath(section, slug), "utf8")
  const parsed = matter(raw)
  return {
    meta: normalizeMeta(section, slug, parsed.data as ArticleFrontmatter, getRegistryMeta(section, slug)),
    body: parsed.content,
  }
}

export function getSiblingArticles(section: ArticleSection, slug: string): {
  previous: ArticleMeta | null
  next: ArticleMeta | null
} {
  const articles = listSectionArticles(section)
  const currentIndex = articles.findIndex((article) => article.slug === slug)

  return {
    previous: currentIndex > 0 ? articles[currentIndex - 1] : null,
    next: currentIndex >= 0 && currentIndex < articles.length - 1 ? articles[currentIndex + 1] : null,
  }
}
