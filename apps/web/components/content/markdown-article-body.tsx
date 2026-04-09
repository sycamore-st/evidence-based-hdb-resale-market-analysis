"use client"

import ReactMarkdown from "react-markdown"
import rehypeKatex from "rehype-katex"
import rehypeRaw from "rehype-raw"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"

import { resolveMarkdownUrl } from "@/lib/markdown-url"

export function MarkdownArticleBody({ body }: { body: string }) {
  return (
    <div className="article-prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeRaw, rehypeKatex]}
        components={{
          a: ({ href = "", children }) => {
            const resolvedHref = resolveMarkdownUrl(href)
            const isExternal = /^https?:\/\//.test(resolvedHref)

            return (
              <a
                href={resolvedHref}
                className="article-link"
                target={isExternal ? "_blank" : undefined}
                rel={isExternal ? "noreferrer" : undefined}
              >
                {children}
              </a>
            )
          },
          img: ({ src = "", alt = "" }) => {
            const resolvedSrc = typeof src === "string" ? resolveMarkdownUrl(src) : ""

            return (
              <img src={resolvedSrc} alt={alt} className="article-inline-image" />
            )
          },
          code: ({ className, children }) => {
            const language = className?.match(/language-([\w-]+)/)?.[1]
            const code = String(children).replace(/\n$/, "")

            if (!language) {
              return <code>{children}</code>
            }

            return (
              <div className="article-code-shell">
                <div className="article-code-header">
                  <div className="article-code-header-left">
                    <span className="article-code-header-chip">{language}</span>
                  </div>
                  <div className="article-code-header-right">
                    <span />
                    <span />
                  </div>
                </div>
                <SyntaxHighlighter
                  language={language}
                  style={oneLight}
                  showLineNumbers
                  wrapLongLines
                  PreTag="div"
                  className="article-code-block"
                  codeTagProps={{ className: "article-code-block-inner" }}
                  customStyle={{ margin: 0, background: "transparent", padding: 0 }}
                  lineNumberStyle={{
                    minWidth: "2.4rem",
                    paddingRight: "1rem",
                    color: "rgba(119, 111, 100, 0.58)",
                  }}
                >
                  {code}
                </SyntaxHighlighter>
              </div>
            )
          },
          blockquote: ({ children }) => <blockquote className="article-quote">{children}</blockquote>,
          table: ({ children }) => (
            <div className="article-table-wrap">
              <table>{children}</table>
            </div>
          ),
          iframe: ({ src = "", title = "Embedded content" }) => {
            const resolvedSrc = typeof src === "string" ? resolveMarkdownUrl(src) : ""

            return (
              <div className="article-embed-shell">
                <iframe src={resolvedSrc} title={title} className="article-embed-frame" loading="lazy" />
              </div>
            )
          },
        }}
      >
        {body}
      </ReactMarkdown>
    </div>
  )
}
