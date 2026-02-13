"use client"

import { useMemo } from "react"
import { cn } from "@/lib/utils"

type Props = {
  content: string
  className?: string
}

type ListType = "ul" | "ol" | null

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
}

function escapeAttribute(value: string): string {
  return escapeHtml(value).replace(/`/g, "&#96;")
}

function isSafeUrl(value: string): boolean {
  const normalized = value.trim().toLowerCase()
  return (
    normalized.startsWith("http://")
    || normalized.startsWith("https://")
    || normalized.startsWith("mailto:")
  )
}

function renderInline(raw: string): string {
  const placeholders: string[] = []
  const store = (html: string) => {
    const index = placeholders.push(html) - 1
    return `@@MD_${index}@@`
  }
  const restore = (value: string) =>
    value.replace(/@@MD_(\d+)@@/g, (_, index) => placeholders[Number(index)] ?? "")

  let text = escapeHtml(raw)

  text = text.replace(/`([^`\n]+)`/g, (_, code) =>
    store(
      `<code class="rounded bg-foreground/10 px-1 py-0.5 font-mono text-[0.85em]">${code}</code>`,
    ),
  )

  text = text.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, href) => {
    const decodedHref = href.replace(/&amp;/g, "&")
    if (!isSafeUrl(decodedHref)) {
      return `${label} (${href})`
    }
    const safeHref = escapeAttribute(decodedHref)
    return store(
      `<a href="${safeHref}" target="_blank" rel="noopener noreferrer" class="underline underline-offset-2 text-primary hover:text-primary/80">${label}</a>`,
    )
  })

  text = text.replace(/\*\*([^*\n][\s\S]*?)\*\*/g, "<strong>$1</strong>")
  text = text.replace(/__([^_\n][\s\S]*?)__/g, "<strong>$1</strong>")
  text = text.replace(/\*([^*\n][\s\S]*?)\*/g, "<em>$1</em>")
  text = text.replace(/_([^_\n][\s\S]*?)_/g, "<em>$1</em>")
  text = text.replace(/~~([^~\n][\s\S]*?)~~/g, "<del>$1</del>")

  return restore(text)
}

function renderMarkdownToHtml(markdown: string): string {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n")
  const output: string[] = []
  let inCodeBlock = false
  let codeLines: string[] = []
  let paragraphLines: string[] = []
  let quoteLines: string[] = []
  let listType: ListType = null
  let listItems: string[] = []

  const flushParagraph = () => {
    if (!paragraphLines.length) return
    const text = paragraphLines.join("\n")
    output.push(`<p class="leading-relaxed">${renderInline(text).replace(/\n/g, "<br />")}</p>`)
    paragraphLines = []
  }

  const flushQuote = () => {
    if (!quoteLines.length) return
    const text = quoteLines.map((line) => renderInline(line)).join("<br />")
    output.push(
      `<blockquote class="border-l-2 border-border/60 pl-3 text-muted-foreground leading-relaxed">${text}</blockquote>`,
    )
    quoteLines = []
  }

  const flushList = () => {
    if (!listType || !listItems.length) return
    const tag = listType
    const items = listItems
      .map((item) => `<li class="leading-relaxed">${renderInline(item)}</li>`)
      .join("")
    const listClass = tag === "ul" ? "list-disc pl-5 space-y-1" : "list-decimal pl-5 space-y-1"
    output.push(`<${tag} class="${listClass}">${items}</${tag}>`)
    listType = null
    listItems = []
  }

  const flushCode = () => {
    if (!codeLines.length) {
      output.push(
        '<pre class="overflow-x-auto rounded-xl border border-border/40 bg-background/70 p-3 font-mono text-xs leading-relaxed"><code></code></pre>',
      )
      return
    }
    output.push(
      `<pre class="overflow-x-auto rounded-xl border border-border/40 bg-background/70 p-3 font-mono text-xs leading-relaxed"><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`,
    )
    codeLines = []
  }

  const flushTextBlocks = () => {
    flushParagraph()
    flushQuote()
    flushList()
  }

  for (const line of lines) {
    const trimmed = line.trim()

    if (inCodeBlock) {
      if (trimmed.startsWith("```")) {
        flushCode()
        inCodeBlock = false
      } else {
        codeLines.push(line)
      }
      continue
    }

    if (trimmed.startsWith("```")) {
      flushTextBlocks()
      inCodeBlock = true
      codeLines = []
      continue
    }

    if (!trimmed) {
      flushTextBlocks()
      continue
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.+)$/)
    if (headingMatch) {
      flushTextBlocks()
      const level = Math.min(3, headingMatch[1].length)
      const headingClass = level === 1
        ? "text-base font-semibold"
        : level === 2
          ? "text-sm font-semibold"
          : "text-sm font-medium"
      output.push(`<h${level} class="${headingClass}">${renderInline(headingMatch[2])}</h${level}>`)
      continue
    }

    const quoteMatch = trimmed.match(/^>\s?(.*)$/)
    if (quoteMatch) {
      flushParagraph()
      flushList()
      quoteLines.push(quoteMatch[1])
      continue
    }
    flushQuote()

    const unorderedMatch = trimmed.match(/^[-*+]\s+(.+)$/)
    if (unorderedMatch) {
      flushParagraph()
      if (listType !== "ul") {
        flushList()
        listType = "ul"
      }
      listItems.push(unorderedMatch[1])
      continue
    }

    const orderedMatch = trimmed.match(/^\d+\.\s+(.+)$/)
    if (orderedMatch) {
      flushParagraph()
      if (listType !== "ol") {
        flushList()
        listType = "ol"
      }
      listItems.push(orderedMatch[1])
      continue
    }

    flushList()
    paragraphLines.push(trimmed)
  }

  if (inCodeBlock) {
    flushCode()
  }
  flushTextBlocks()

  return output.join("")
}

export function MarkdownContent({ content, className }: Props) {
  const html = useMemo(() => renderMarkdownToHtml(content || ""), [content])
  return (
    <div
      className={cn("space-y-3 break-words text-sm text-foreground", className)}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
