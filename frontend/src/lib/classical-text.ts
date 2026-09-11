import type { Locale } from "@/i18n/config"

export type ClassicalSource = {
  key: string
  label: string
  content: string
}

export type ClassicalChapter = {
  key: string
  title: string
  lineNo?: number | null
  marked?: boolean
  sources: ClassicalSource[]
}

export function chapterTitle(lineNo: number | null | undefined, useKind: string | null | undefined, locale: Locale) {
  if (useKind) return useKind === "yong_jiu" ? (locale === "zh" ? "用九" : "Use of nine") : useKind === "yong_liu" ? (locale === "zh" ? "用六" : "Use of six") : (locale === "zh" ? "用九 / 用六" : "Use of nine / six")
  if (!lineNo) return locale === "zh" ? "卦辞" : "Judgment"
  return locale === "zh" ? ["", "初爻", "二爻", "三爻", "四爻", "五爻", "上爻"][lineNo] : `Line ${lineNo}`
}

