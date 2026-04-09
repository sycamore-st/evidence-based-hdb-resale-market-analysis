"use client"

import { useEffect, useMemo, useState } from "react"

interface TocItem {
  id: string
  text: string
  level: 2 | 3
}

function slugifyHeading(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
}

export function ArticleScrollspy({ selector = ".article-prose h2, .article-prose h3" }: { selector?: string }) {
  const [items, setItems] = useState<TocItem[]>([])
  const [activeId, setActiveId] = useState<string>("")

  useEffect(() => {
    const headings = Array.from(document.querySelectorAll<HTMLHeadingElement>(selector))
    const usedIds = new Map<string, number>()

    const tocItems: TocItem[] = headings
      .map((heading, index) => {
        const text = heading.textContent?.trim() ?? ""
        if (!text) return null

        const level = heading.tagName === "H2" ? 2 : 3
        const currentId = heading.id?.trim()

        if (!currentId) {
          const base = slugifyHeading(text) || `section-${index + 1}`
          const count = usedIds.get(base) ?? 0
          usedIds.set(base, count + 1)
          heading.id = count === 0 ? base : `${base}-${count + 1}`
        }

        return {
          id: heading.id,
          text,
          level,
        } as TocItem
      })
      .filter((item): item is TocItem => Boolean(item))

    setItems(tocItems)
    setActiveId(tocItems[0]?.id ?? "")

    if (tocItems.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => left.boundingClientRect.top - right.boundingClientRect.top)

        if (visible.length > 0) {
          const id = (visible[0].target as HTMLElement).id
          if (id) setActiveId(id)
        }
      },
      {
        root: null,
        rootMargin: "-20% 0px -65% 0px",
        threshold: [0, 1],
      }
    )

    headings.forEach((heading) => observer.observe(heading))

    return () => {
      observer.disconnect()
    }
  }, [selector])

  const hasItems = useMemo(() => items.length > 0, [items])

  if (!hasItems) return null

  return (
    <aside className="article-scrollspy" aria-label="On this page">
      <p className="article-scrollspy-title">On This Page</p>
      <ol className="article-scrollspy-list">
        {items.map((item) => (
          <li key={item.id} className={`article-scrollspy-item level-${item.level}`}>
            <a
              href={`#${item.id}`}
              className={item.id === activeId ? "is-active" : undefined}
              onClick={() => setActiveId(item.id)}
            >
              {item.text}
            </a>
          </li>
        ))}
      </ol>
    </aside>
  )
}
