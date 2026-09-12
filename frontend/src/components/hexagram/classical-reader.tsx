"use client"

import { useId, useRef, useState } from "react"
import { ArrowLeft, ArrowRight, Check } from "lucide-react"
import type { Locale } from "@/i18n/config"
import type { ClassicalChapter, ClassicalSource } from "@/lib/classical-text"

const SOURCE_ORDER = ["guaci", "takashima", "english_commentary", "symbolic"]
const SOURCE_NAMES: Record<string, { zh: string; en: string }> = {
  guaci: { zh: "经传与中文注解", en: "Chinese text & commentary" },
  takashima: { zh: "高岛易断", en: "Takashima" },
  english_commentary: { zh: "英译与注释", en: "English translations & commentary" },
  symbolic: { zh: "八卦象意", en: "Trigram imagery" },
}

function sourceName(source: ClassicalSource, locale: Locale) {
  return SOURCE_NAMES[source.key]?.[locale] ?? source.label
}

/** Formats the stored text; every non-empty source line remains in its original order. */
export function ClassicalText({ content, source }: { content: string; source: string }) {
  const lines = content.split(/\r?\n/)
  const englishHeading = /^(?:Judgment|The Judgment|The Image|Image|Commentary|Notes and Paraphrases|Notes|Paraphrase|Line[- ]\d+|Editor['’]s Notes)\s*$/i
  const author = /^(Legge|Wilhelm\s*\/\s*Baynes|Blofeld|Liu|Ritsema\s*\/\s*Karcher|Shaughnessy|Cleary\s*\([12]\)|Cleary|Wu|Confucius\s*\/\s*Legge)\s*:/
  return <div className="classical-prose" lang={source === "english_commentary" ? "en" : "zh"}>
    {lines.map((line, index) => {
      const text = line.trim()
      if (!text) return <div className="classical-paragraph-break" key={index} aria-hidden="true" />
      if ((source === "english_commentary" && englishHeading.test(text)) || /^(?:北宋易学家邵雍解|台湾国学大儒傅佩荣解)$/.test(text)) {
        return <h4 key={index}>{text}</h4>
      }
      const match = source === "english_commentary" ? text.match(author) : null
      if (match) return <p className="classical-translation" key={index}><strong>{match[0]}</strong>{text.slice(match[0].length)}</p>
      if (source === "guaci" && ((index === 0 && !/(?:详解|爻辞|哲学含义)/.test(text)) || /^(?:象曰|彖曰|《象》曰|《彖》曰)[：:]/.test(text))) return <blockquote key={index}>{text}</blockquote>
      if (source === "takashima" && /^【(?:占|例)】/.test(text)) return <p className="classical-case" key={index}>{text}</p>
      return <p key={index}>{text}</p>
    })}
  </div>
}

export function ClassicalReader({ chapters, locale, initialChapter, heading, singleSource = false }: {
  chapters: ClassicalChapter[]
  locale: Locale
  initialChapter?: string
  heading?: string
  singleSource?: boolean
}) {
  const [activeKey, setActiveKey] = useState(initialChapter ?? chapters[0]?.key)
  const [selectedSource, setSelectedSource] = useState<string | null>(null)
  const [hiddenSources, setHiddenSources] = useState<string[]>([])
  const root = useRef<HTMLDivElement>(null)
  const id = useId()
  const chapter = chapters.find((item) => item.key === activeKey) ?? chapters[0]
  if (!chapter) return null
  const index = chapters.indexOf(chapter)
  const sources = [...chapter.sources].sort((a, b) => {
    const rank = (key: string) => SOURCE_ORDER.includes(key) ? SOURCE_ORDER.indexOf(key) : SOURCE_ORDER.length
    return rank(a.key) - rank(b.key)
  })
  const visible = sources.filter((source) => !hiddenSources.includes(source.key))
  const shownSources = singleSource ? [sources.find((source) => source.key === selectedSource) ?? sources[0]].filter(Boolean) : visible.length ? visible : sources
  const selectChapter = (key: string) => {
    setActiveKey(key)
    root.current?.scrollIntoView({ block: "start" })
  }
  return <div className="classical-reader" data-single-source={singleSource || undefined} ref={root}>
    <nav className="classical-chapters" aria-label={locale === "zh" ? "卦辞与六爻章节" : "Judgment and line chapters"}>
      <p className="classical-nav-title">{heading ?? (locale === "zh" ? "经传对读" : "Read the sources")}</p>
      {chapters.map((item) => <button type="button" key={item.key} aria-pressed={chapter.key === item.key} aria-controls={`${id}-chapter`} onClick={() => selectChapter(item.key)}>
        <span className="classical-chapter-number">{item.lineNo ? String(item.lineNo).padStart(2, "0") : item.key.includes("use") ? (locale === "zh" ? "用" : "Use") : (locale === "zh" ? "卦" : "Text")}</span>
        <span>{item.title}</span>
        {item.marked ? <span className="classical-moving-label">{locale === "zh" ? "取用" : "Focus"}</span> : null}
      </button>)}
      <p className="classical-nav-note">{locale === "zh" ? "自初至上，逐爻对读。各家说法保留原有署名与文字。" : "Read from the first line upward. Each source retains its wording and attribution."}</p>
    </nav>
    <section id={`${id}-chapter`} className="classical-chapter-content" aria-label={chapter.title}>
      <header className="classical-chapter-header">
        <div><p className="kicker">{locale === "zh" ? "经文 · 注解 · 占例" : "Text · commentary · examples"}</p><h2>{chapter.title}</h2></div>
        <div className="classical-page-buttons">
          <button type="button" disabled={index === 0} onClick={() => selectChapter(chapters[index - 1].key)} aria-label={locale === "zh" ? "上一章" : "Previous chapter"}><ArrowLeft size={16} aria-hidden="true" /></button>
          <span>{index + 1} / {chapters.length}</span>
          <button type="button" disabled={index === chapters.length - 1} onClick={() => selectChapter(chapters[index + 1].key)} aria-label={locale === "zh" ? "下一章" : "Next chapter"}><ArrowRight size={16} aria-hidden="true" /></button>
        </div>
      </header>
      <div className="classical-source-switches" role="group" aria-label={locale === "zh" ? "选择对读来源" : "Choose sources to compare"}>
        {sources.map((source) => <button key={source.key} type="button" aria-pressed={shownSources.includes(source)} onClick={() => {
          if (singleSource) { setSelectedSource(source.key); return }
          if (shownSources.length === 1 && shownSources[0].key === source.key) return
          setHiddenSources((current) => current.includes(source.key) ? current.filter((key) => key !== source.key) : [...current, source.key])
        }}><Check size={13} aria-hidden="true" /><span>{sourceName(source, locale)}</span></button>)}
      </div>
      <div className="classical-sources" data-count={shownSources.length}>
        {shownSources.map((source) => <article key={source.key} className="classical-source" data-source={source.key}>
          <header><h3>{sourceName(source, locale)}</h3><p>{source.key === "guaci" ? (locale === "zh" ? "卦辞库 · 经文与各家注解合编" : "Received text and collected Chinese interpretations") : source.key === "takashima" ? (locale === "zh" ? "高岛易断 · 中文收录本" : "Takashima · Chinese text in this archive") : source.key === "english_commentary" ? (locale === "zh" ? "各译者署名见正文" : "Translators are named in the text") : source.label}</p></header>
          <ClassicalText content={source.content} source={source.key} />
        </article>)}
      </div>
      <footer className="classical-chapter-footer">
        <span>{locale === "zh" ? `${chapter.title} · 本章所选来源全文` : `${chapter.title} · complete selected source texts`}</span>
        {index < chapters.length - 1 ? <button type="button" onClick={() => selectChapter(chapters[index + 1].key)}>{chapters[index + 1].title}<ArrowRight size={15} aria-hidden="true" /></button> : null}
      </footer>
    </section>
  </div>
}
