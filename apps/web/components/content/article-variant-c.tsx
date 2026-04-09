"use client"

import { useEffect, useState } from "react"
import Link from "next/link"

import { ArticlePager } from "@/components/content/article-shell"
import { ArticleScrollspy } from "@/components/content/article-scrollspy"
import { MarkdownArticleBody } from "@/components/content/markdown-article-body"
import type { ArticleDocument, ArticleMeta, ArticleSection } from "@/lib/content"

export function ArticleVariantC({
  article,
  section,
  previous,
  next,
}: {
  article: ArticleDocument
  section: ArticleSection
  previous: ArticleMeta | null
  next: ArticleMeta | null
}) {
  const [panelWidth, setPanelWidth] = useState(420)
  const [dragging, setDragging] = useState(false)

  useEffect(() => {
    if (!dragging) {
      return
    }

    const handleMove = (event: PointerEvent) => {
      const viewportWidth = window.innerWidth
      const nextWidth = Math.min(Math.max(event.clientX, 320), Math.min(640, Math.floor(viewportWidth * 0.5)))
      setPanelWidth(nextWidth)
    }

    const stopDragging = () => {
      setDragging(false)
    }

    window.addEventListener("pointermove", handleMove)
    window.addEventListener("pointerup", stopDragging)

    return () => {
      window.removeEventListener("pointermove", handleMove)
      window.removeEventListener("pointerup", stopDragging)
    }
  }, [dragging])

  return (
    <main className="article-page article-page-c" style={{ ["--article-panel-width" as string]: `${panelWidth}px` }}>
      <section className="article-scene-c">
        <aside className="article-panel-c">
          <div className="article-panel-c-brand">HDB Resale Web</div>

          <div className="article-panel-c-copy">
            <p>{article.meta.kicker}</p>
            <h1>{article.meta.title}</h1>
          </div>

          <div className="article-panel-c-actions">
            <Link href={`/${section}`}>Open section</Link>
            <Link href="/#menu">Menu</Link>
          </div>

          <div className="article-panel-c-meta">
            <small>{article.meta.readingLabel}</small>
            <strong>{section === "section2" ? "Markdown case note" : "Markdown policy note"}</strong>
          </div>

          <button
            type="button"
            className={`article-panel-c-resize${dragging ? " article-panel-c-resize-active" : ""}`}
            aria-label="Resize side panel"
            onPointerDown={(event) => {
              event.preventDefault()
              setDragging(true)
            }}
          />
        </aside>

        <div className="article-content-c">
          <div className="article-content-c-topnav">
            <nav>
              <Link href="/section1">Section 1</Link>
              <Link href="/section2">Section 2</Link>
              <Link href="/section3">Section 3</Link>
            </nav>
            <Link href="/#menu" className="article-content-c-home">
              Menu
            </Link>
          </div>

          <div className="article-reading-layout">
            <article className="article-card article-card-c">
              <MarkdownArticleBody body={article.body} />
              <ArticlePager section={section} previous={previous} next={next} />
            </article>
            <ArticleScrollspy />
          </div>
        </div>
      </section>
    </main>
  )
}
