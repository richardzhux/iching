import type { MetaphysicsChart } from "@/types/api"
import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"
import type { IFunctionalHoroscope } from "iztro/lib/astro/FunctionalHoroscope"

type Locale = "en" | "zh"

const cell = (value: string) => value.replaceAll("|", "\\|").replaceAll("\n", "<br>") || "—"

export function buildBaziMarkdown(chart: MetaphysicsChart, subjectName: string, locale: Locale) {
  const zh = locale === "zh"
  const title = subjectName.trim() || (zh ? "未命名命盘" : "Personal chart")
  const labels = zh
    ? ["干神", "天干", "地支", "藏干", "支神", "纳音", "空亡", "地势", "自坐"]
    : ["Stem relation", "Stem", "Branch", "Hidden stems", "Hidden relations", "Na Yin", "Void", "Life stage", "Self seat"]
  const rows = [
    chart.pillars.map((pillar) => pillar.ten_god),
    chart.pillars.map((pillar) => `${pillar.stem}·${pillar.stem_element}`),
    chart.pillars.map((pillar) => `${pillar.branch}·${pillar.branch_element}`),
    chart.pillars.map((pillar) => pillar.hidden_stems.map((item) => `${item.stem}·${item.element}`).join(" / ") || "—"),
    chart.pillars.map((pillar) => pillar.hidden_stems.map((item) => item.ten_god).join(" / ") || "—"),
    chart.pillars.map((pillar) => pillar.nayin),
    chart.pillars.map((pillar) => pillar.xunkong ?? "—"),
    chart.pillars.map((pillar) => pillar.di_shi ?? "—"),
    chart.pillars.map((pillar) => pillar.self_seat ?? "—"),
  ]
  const headings = zh ? [title, "年柱", "月柱", "日柱", "时柱"] : [title, "Year", "Month", "Day", "Hour"]
  const table = [
    `| ${headings.map(cell).join(" | ")} |`,
    `| ${headings.map(() => "---").join(" | ")} |`,
    ...rows.map((values, index) => `| ${cell(labels[index])} | ${values.map(cell).join(" | ")} |`),
  ]
  const seasonal = Object.entries(chart.element_season_status ?? {}).map(([element, status]) => `${element}${status}`).join(" / ") || "—"
  const facts = zh
    ? [
        `天干关系：${(chart.stem_relations ?? []).join(" / ") || "无显著冲克"}`,
        `地支关系：${(chart.branch_relations ?? []).join(" / ") || "无显著合冲刑害破"}`,
        `五行时令：${seasonal}`,
      ]
    : [
        `Stem relations: ${(chart.stem_relations ?? []).join(" / ") || "None listed"}`,
        `Branch relations: ${(chart.branch_relations ?? []).join(" / ") || "None listed"}`,
        `Seasonal element state: ${seasonal}`,
      ]
  return [`## ${zh ? "命主" : "Chart"}：${title}`, "", `## ${zh ? "生辰八字" : "BaZi"}`, "", ...table, "", ...facts].join("\n")
}

export function buildZiweiMarkdown(
  chart: IFunctionalAstrolabe,
  horoscope: IFunctionalHoroscope,
  subjectName: string,
  locale: Locale,
) {
  const zh = locale === "zh"
  const title = subjectName.trim() || (zh ? "匿名命主" : "Anonymous chart")
  const transformations = chart.palaces
    .flatMap((palace) => [...palace.majorStars, ...palace.minorStars]
      .filter((star) => star.mutagen)
      .map((star) => `${star.name}化${star.mutagen}（${palace.name}）`))
    .join(" / ") || "—"
  const summary = [
    [zh ? "阳历" : "Solar date", `${chart.solarDate} ${chart.time}（${chart.gender}）`],
    [zh ? "农历" : "Lunar date", `${chart.lunarDate} ${chart.time}`],
    [zh ? "干支" : "Chinese date", chart.chineseDate],
    [zh ? "五行局" : "Five-element class", chart.fiveElementsClass],
    [zh ? "生年四化" : "Natal transformations", transformations],
    [zh ? "命主" : "Soul ruler", chart.soul],
    [zh ? "身主" : "Body ruler", chart.body],
    [zh ? "运限日期" : "Horoscope date", `${horoscope.solarDate} / ${horoscope.lunarDate}`],
  ]
  const summaryTable = [
    `| ${zh ? "项目" : "Item"} | ${zh ? "内容" : "Value"} |`,
    "| --- | --- |",
    ...summary.map(([label, value]) => `| ${cell(label)} | ${cell(value)} |`),
  ]
  const palaceTable = [
    `| ${zh ? "宫位" : "Stem/branch"} | ${zh ? "宫名" : "Palace"} | ${zh ? "大限" : "Decadal"} | ${zh ? "小限" : "Ages"} | ${zh ? "星曜与状态" : "Stars and states"} |`,
    "| --- | --- | --- | --- | --- |",
    ...chart.palaces.map((palace) => {
      const stars = [...palace.majorStars, ...palace.minorStars, ...palace.adjectiveStars]
        .map((star) => `${star.name}${star.brightness ? `(${star.brightness})` : ""}${star.mutagen ? `·化${star.mutagen}` : ""}`)
      const states = [palace.changsheng12, palace.boshi12, palace.jiangqian12, palace.suiqian12].filter(Boolean)
      return `| ${cell(`${palace.heavenlyStem}${palace.earthlyBranch}`)} | ${cell(`${palace.name}${palace.isBodyPalace ? (zh ? "（身宫）" : " (Body)") : ""}`)} | ${cell(`${palace.decadal.range[0]}–${palace.decadal.range[1]}`)} | ${cell(palace.ages.join(" "))} | ${cell([...stars, ...states].join("、"))} |`
    }),
  ]
  return [
    `## ${zh ? "命主" : "Chart"}：${title}`,
    "",
    `## ${zh ? "紫微斗数" : "Zi Wei Dou Shu"}`,
    "",
    ...summaryTable,
    "",
    ...palaceTable,
  ].join("\n")
}
