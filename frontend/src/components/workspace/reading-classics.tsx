"use client"

import { useState } from "react"
import type { Locale } from "@/i18n/config"
import { ClassicalReader } from "@/components/hexagram/classical-reader"
import { chapterTitle, type ClassicalChapter } from "@/lib/classical-text"
import type { HexSection, SessionPayload } from "@/types/api"

function buildChapters(sections: HexSection[], locale: Locale) {
  const chapters = new Map<string, ClassicalChapter>()
  for (const section of sections) {
    if (!section.content || (locale === "en" ? section.source !== "english_commentary" : section.source === "english_commentary")) continue
    const line = section.line_key && section.line_key !== "all" ? Number(section.line_key) : null
    const useKind = section.line_key === "all" ? ((section.hexagram_name.includes("乾") || section.hexagram_name === "The Creative") ? "yong_jiu" : "yong_liu") : null
    const key = useKind ? `use-${useKind}` : line ? `line-${line}` : "gua"
    const chapter = chapters.get(key) ?? { key, title: chapterTitle(line, useKind, locale), lineNo: line, sources: [] }
    chapter.marked = chapter.marked || (section.visible_by_default && section.importance === "primary")
    chapter.sources.push({ key: section.source ?? section.id, label: section.source_label ?? section.title, content: section.content })
    chapters.set(key, chapter)
  }
  return [...chapters.values()].sort((a, b) => (a.key.startsWith("use") ? 7 : a.lineNo ?? 0) - (b.key.startsWith("use") ? 7 : b.lineNo ?? 0))
}

export function ReadingClassics({ result, locale }: { result: SessionPayload; locale: Locale }) {
  const [selected, setSelected] = useState<"main" | "changed">("main")
  const type = selected === "changed" && !result.hex_overview.changed_hexagram ? "main" : selected
  const chapters = buildChapters((result.hex_sections ?? []).filter((section) => section.hexagram_type === type), locale)
  if (!chapters.length) return null
  const focused = chapters.find((chapter) => chapter.marked && chapter.key !== "gua") ?? chapters[0]
  const name = type === "main" ? result.hex_overview.main_hexagram.name : result.hex_overview.changed_hexagram?.name
  return <section className="reading-classics" id="reading-classics">
    <header className="reading-classics-heading"><div><p className="kicker">{locale === "zh" ? "本次卦例的经典资料" : "Sources for this reading"}</p><h2>{locale === "zh" ? "逐爻对读" : "Read by chapter"}</h2></div><div className="reading-classics-choice" role="group" aria-label={locale === "zh" ? "选择阅读本卦或变卦" : "Choose primary or changed texts"}>
      <button type="button" aria-pressed={type === "main"} onClick={() => setSelected("main")}>{locale === "zh" ? "本卦" : "Primary"} · {result.hex_overview.main_hexagram.name}</button>
      {result.hex_overview.changed_hexagram ? <button type="button" aria-pressed={type === "changed"} onClick={() => setSelected("changed")}>{locale === "zh" ? "变卦" : "Changed"} · {result.hex_overview.changed_hexagram.name}</button> : null}
    </div></header>
    <ClassicalReader singleSource key={`${result.session_id}-${type}`} chapters={chapters} locale={locale} initialChapter={focused.key} heading={name} />
  </section>
}
