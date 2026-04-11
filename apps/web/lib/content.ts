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
      title: "How far can three fields get you?",
      kicker: "Pricing accuracy",
      description: "We tried predicting resale prices using only town, flat type, and flat age. Here's how close we got — and where the model breaks down.",
      order: 1,
      readingLabel: "Prediction under limited inputs",
    },
    {
      section: "section2",
      slug: "question-b",
      title: "Is this flat overpriced?",
      kicker: "Valuation check",
      description: "A practical framework for spotting outliers — combining expected-price models with local context and comparable transactions.",
      order: 2,
      readingLabel: "Valuation and comparable context",
    },
    {
      section: "section2",
      slug: "question-c",
      title: "Recovering what the data hides",
      kicker: "Hidden features",
      description: "When flat type is missing from the record, can we reliably guess it back — and does getting it wrong hurt the pricing model?",
      order: 4,
      readingLabel: "Recovery of hidden categories",
    },
    {
      section: "section2",
      slug: "question-b-extended",
      title: "The valuation workbench",
      kicker: "Interactive tool",
      description: "An interactive sandbox to explore expected prices, local distributions, and comparable sales for any transaction.",
      order: 3,
      readingLabel: "Interactive valuation workflow",
    },
  ],
  section3: [
    {
      section: "section3",
      slug: "question-a",
      title: "Is Yishun really that cheap?",
      kicker: "Town comparison",
      description: "Everyone says Yishun is the budget pick. We controlled for flat type and age to see if the discount is real — or just a mix effect.",
      order: 1,
      readingLabel: "Town-level value comparison",
    },
    {
      section: "section3",
      slug: "question-b",
      title: "Are flats actually getting smaller?",
      kicker: "Space trends",
      description: "New flats feel smaller, but is that because units shrank — or because more small types are being sold? We untangled the two.",
      order: 2,
      readingLabel: "Space trends and composition effects",
    },
    {
      section: "section3",
      slug: "question-c",
      title: "What a new MRT line does to prices",
      kicker: "Transit impact",
      description: "When Downtown Line Stage 2 opened, did nearby flats actually gain value? A before-and-after comparison with control towns.",
      order: 3,
      readingLabel: "Transit and pricing impact",
    },
    {
      section: "section3",
      slug: "question-d",
      title: "Do outer towns feel COE changes more?",
      kicker: "Policy sensitivity",
      description: "COE premiums ripple through the market differently depending on where you live. We measured who gets hit hardest.",
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
