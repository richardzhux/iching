import type { ConsumerProfile, MetaphysicsChart, MetaphysicsStatistics } from "@/types/api"
import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"
import type { IFunctionalHoroscope } from "iztro/lib/astro/FunctionalHoroscope"

type Locale = "en" | "zh"

const cell = (value: string) => value.replaceAll("|", "\\|").replaceAll("\n", "<br>") || "—"

function consumerMarkdown(consumer: ConsumerProfile | undefined, zh: boolean) {
  if (!consumer?.identity) return []
  const identity = consumer.identity
  const subjectTable = [
    `| ${zh ? "人生主题" : "Life theme"} | ${zh ? "表达路径" : "Expression path"} | ${zh ? "说明" : "Meaning"} |`,
    "| --- | --- | --- |",
    ...consumer.subjects.map((subject) => `| ${cell(subject.label)} | ${cell(subject.path_label || subject.headline || (zh ? "结构路径" : "Structural path"))} | ${cell(subject.path_summary || (subject.drivers ?? []).slice(0, 2).join(" · ") || (zh ? "查看完整命盘" : "See full chart"))} |`),
  ]
  const stages = consumer.life_kline.stages.slice(0, 3).map((stage) => `- ${stage.year}｜**${stage.label}**：${zh ? "值得关注的阶段" : "A period worth watching"}`)
  return [
    `## ${zh ? "命格身份" : "Chart identity"}`,
    "",
    `### ${identity.fusion_title || identity.archetype_title}`,
    "",
    identity.archetype_subtitle,
    "",
    `**${zh ? "你的四条人生路径" : "Your four life paths"}**`,
    "",
    ...subjectTable,
    ...(stages.length ? ["", `### ${zh ? "未来三大阶段" : "Three future stages"}`, "", ...stages] : []),
    "",
  ]
}

function ziweiMetricMarkdownLabel(featureId: string, chart: IFunctionalAstrolabe, zh: boolean) {
  const life = chart.palaces.find((palace) => palace.name === "命宫" || palace.name.toLowerCase().includes("soul"))
  const body = chart.palaces.find((palace) => palace.isBodyPalace)
  if (featureId.includes(".life_combo.")) return zh ? `命宫主星 · ${life?.majorStars.map((star) => star.name).join("、") || "空宫"}` : `Life-palace stars · ${life?.majorStars.map((star) => star.name).join(", ") || "empty"}`
  if (featureId.includes(".body_branch.")) return zh ? `身宫位置 · ${body?.name ?? "—"}` : `Body-palace position · ${body?.name ?? "—"}`
  if (featureId.includes(".five_elements.")) return zh ? `五行局 · ${chart.fiveElementsClass}` : `Five-element class · ${chart.fiveElementsClass}`
  if (featureId.includes(".empty_palaces.")) return zh ? `空宫数量 · ${featureId.split(".").at(-1)}` : `Empty palaces · ${featureId.split(".").at(-1)}`
  if (featureId.includes(".brightness.")) {
    const [slug, count] = featureId.split(".").slice(-2)
    const label = zh
      ? ({ miao: "庙", wang: "旺", de: "得", li: "利", ping: "平", xian: "陷", unmarked: "未标" } as Record<string, string>)[slug] ?? slug
      : ({ miao: "Temple", wang: "Prosperous", de: "Favorable", li: "Supported", ping: "Neutral", xian: "Weak", unmarked: "Unmarked" } as Record<string, string>)[slug] ?? slug
    return zh ? `主星亮度结构 · ${label} ${count}` : `Major-star brightness · ${label} ${count}`
  }
  if (featureId.includes(".mutagen.")) {
    const parts = featureId.split(".")
    const mutagen = ({ lu: "禄", quan: "权", ke: "科", ji: "忌" } as Record<string, string>)[parts.at(-2) ?? ""] ?? parts.at(-2)
    const palaceIndex = Number(parts.at(-1)?.replace("palace-", ""))
    return zh ? `化${mutagen}落宫 · ${chart.palaces.find((item) => item.index === palaceIndex)?.name ?? parts.at(-1)}` : `Transformation ${mutagen} placement · ${chart.palaces.find((item) => item.index === palaceIndex)?.name ?? parts.at(-1)}`
  }
  if (featureId.includes(".auspicious_palaces.")) return zh ? `六吉星分布宫数 · ${featureId.split(".").at(-1)}` : `Six-auxiliary distribution · ${featureId.split(".").at(-1)} palaces`
  if (featureId.includes(".auspicious_max_density.")) return zh ? `六吉星单宫最高数 · ${featureId.split(".").at(-1)}` : `Max six-auxiliary density · ${featureId.split(".").at(-1)}`
  if (featureId.includes(".challenging_palaces.")) return zh ? `六煞星分布宫数 · ${featureId.split(".").at(-1)}` : `Six-challenging distribution · ${featureId.split(".").at(-1)} palaces`
  if (featureId.includes(".challenging_max_density.")) return zh ? `六煞星单宫最高数 · ${featureId.split(".").at(-1)}` : `Max six-challenging density · ${featureId.split(".").at(-1)}`
  return zh ? "结构特征" : "Structural feature"
}

export function buildBaziMarkdown(chart: MetaphysicsChart, subjectName: string, locale: Locale) {
  const zh = locale === "zh"
  const title = subjectName.trim() || (zh ? "未命名命盘" : "Personal chart")
  if (chart.birth_profile.hour_uncertain) {
    const stability = chart.birth_profile.stability
    return [
      `## ${zh ? "命主" : "Chart"}：${title}`,
      "",
      `## ${zh ? "不受时辰影响的部分" : "Stable across possible birth hours"}`,
      "",
      ...(stability?.stable_pillars ?? []).map((item) => `- ${item.label}${zh ? "柱" : " pillar"}：${item.text}`),
      "",
      ...(chart.synthesis?.conclusions ?? []).map((item) => `- **${item.headline}**：${item.body}`),
      "",
      `## ${zh ? "稳定命中的核心线索" : "Stable supporting markers"}`,
      "",
      ...(stability?.stable_shensha ?? []).map((name) => `- ${name}`),
      "",
      `## ${zh ? "确认时辰后会进一步明确" : "What the exact hour will clarify"}`,
      "",
      ...(stability?.sensitive_items ?? []).map((item) => `- ${item.label}：${item.detail}`),
      "",
      `> ${zh ? `已对照 ${stability?.candidate_count ?? 13} 个可能时辰；这里仅保留全部候选中都成立的内容。` : `Compared ${stability?.candidate_count ?? 13} possible hours; only stable findings are included here.`}`,
    ].join("\n")
  }
  const labels = zh
    ? ["干神", "天干", "地支", "藏干", "支神", "纳音", "空亡", "地势", "自坐", "神煞"]
    : ["Stem relation", "Stem", "Branch", "Hidden stems", "Hidden relations", "Na Yin", "Void", "Life stage", "Self seat", "Shen Sha"]
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
    chart.pillars.map((pillar) => chart.shen_sha.filter((hit) => hit.pillar_labels.includes(pillar.label)).map((hit) => hit.name).join(" / ") || "—"),
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
        `日主结构：${chart.structure.day_master.stem}${chart.structure.day_master.element} · 月令${chart.structure.day_master.month_status} · ${chart.structure.day_master.rooted ? `通根于${chart.structure.day_master.root_pillars.join("、")}柱` : "未见同类藏干根气"}`,
        `天干关系：${(chart.stem_relations ?? []).join(" / ") || "无显著冲克"}`,
        `地支关系：${(chart.branch_relations ?? []).join(" / ") || "无显著合冲刑害破"}`,
        `五行时令：${seasonal}`,
      ]
    : [
        `Day-master structure: ${chart.structure.day_master.stem} ${chart.structure.day_master.element} · month state ${chart.structure.day_master.month_status} · ${chart.structure.day_master.rooted ? `roots in ${chart.structure.day_master.root_pillars.join(", ")}` : "no same-element hidden root recorded"}`,
        `Stem relations: ${(chart.stem_relations ?? []).join(" / ") || "None listed"}`,
        `Branch relations: ${(chart.branch_relations ?? []).join(" / ") || "None listed"}`,
        `Seasonal element state: ${seasonal}`,
      ]
  const shensha = chart.shen_sha.map((hit) => {
    const rarity = chart.statistics.rarity_metrics.find((metric) => metric.feature_id === hit.feature_id)
    const frequency = rarity?.status === "unsupported" ? (zh ? "暂无基线数据" : "No baseline data") : rarity?.display_percentage ?? "—"
    return `- ${hit.name}｜${hit.pillar_labels.join("、")}${zh ? "柱" : " pillar"}｜${frequency}｜${hit.source.title}`
  })
  const dayun = chart.birth_profile.dayun.cycles.length ? [
    `## ${zh ? "大运" : "Da Yun"}`,
    "",
    `| ${zh ? "干支" : "Pillar"} | ${zh ? "年龄" : "Ages"} | ${zh ? "年份" : "Years"} | ${zh ? "十神" : "Ten God"} |`,
    "| --- | --- | --- | --- |",
    ...chart.birth_profile.dayun.cycles.map((cycle) => `| ${cell(cycle.ganzhi || cycle.label)} | ${cycle.start_age}–${cycle.end_age} | ${cycle.start_year}–${cycle.end_year} | ${cell(cycle.ten_god || "—")} |`),
    "",
  ] : []
  const themes = (chart.theme_profiles ?? chart.structure?.theme_profiles ?? []).flatMap((profile) => [
    `### ${profile.theme}`,
    ...(profile.comparisons ?? []).map((item) => item.comparison_mode === "incidence"
      ? `- ${item.label} ${item.value ? (zh ? "命中" : "present") : (zh ? "未命中" : "absent")}：${zh ? "出现率" : "incidence"} ${(item.hit_percentage ?? 0).toFixed(1)}%`
      : `- ${item.label} ${item.value}：${zh ? "低于" : "lower"} ${(item.lower_percentage ?? 0).toFixed(1)}% · ${zh ? "相同" : "same"} ${(item.same_percentage ?? 0).toFixed(1)}% · ${zh ? "高于" : "higher"} ${(item.higher_percentage ?? 0).toFixed(1)}%`),
    ...profile.evidence.map((item) => `- ${item.evidence_type}｜${item.title}：${item.detail}（${item.source}）`),
  ])
  return [
    `## ${zh ? "命主" : "Chart"}：${title}`, "", ...consumerMarkdown(chart.consumer, zh), `## ${zh ? "生辰八字" : "BaZi"}`, "", ...table, "", ...facts,
    "", ...dayun,
    "", `## ${zh ? "神煞与历法样本频率" : "Shen Sha and calendar-sample frequency"}`, "", ...shensha,
    "", `> ${zh ? "出现率只表示这项结构在历法样本中的少见程度，不代表吉凶或人生高低。" : "Incidence only describes how uncommon a structure is in calendar samples; it does not indicate fortune or life quality."}`,
    "", `## ${zh ? "核心判断" : "Key findings"}`, "", ...(chart.synthesis?.conclusions ?? []).map((item) => `- **${item.headline}**：${item.body}${item.distribution_context ? `（${item.distribution_context}）` : ""}`),
    "", `## ${zh ? "四主题结构画像" : "Four-theme structure profile"}`, "", ...themes,
    "", `> ${zh ? "规则版本" : "Rules"}: ${chart.rules_version} · ${zh ? "统计基线" : "Baseline"}: ${chart.statistics.baseline.id}`,
  ].join("\n")
}

export function buildZiweiMarkdown(
  chart: IFunctionalAstrolabe,
  horoscope: IFunctionalHoroscope,
  subjectName: string,
  locale: Locale,
  statistics?: MetaphysicsStatistics,
  context?: {
    archiveMode: "standard" | "legacy-static" | "legacy-nonstandard"
    provenance: {
      configId?: string
      algorithm: "default" | "zhongzhou"
      astroType: "heaven" | "earth" | "human"
      yearDivide: "normal" | "exact"
      dayBoundary: "current" | "forward"
      calendar: "solar" | "lunar"
      fixLeap: boolean
      isLeapMonth: boolean
    }
    consumer?: ConsumerProfile
  },
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
  const periodItems = [
    [zh ? "大限" : "Decadal", horoscope.decadal],
    [zh ? "流年" : "Yearly", horoscope.yearly],
    [zh ? "流月" : "Monthly", horoscope.monthly],
    [zh ? "流日" : "Daily", horoscope.daily],
    [zh ? "流时" : "Hourly", horoscope.hourly],
  ] as const
  const periodTable = [
    `| ${zh ? "层级" : "Layer"} | ${zh ? "干支" : "Pillar"} | ${zh ? "名称" : "Name"} | ${zh ? "四化" : "Transformations"} |`,
    "| --- | --- | --- | --- |",
    `| ${zh ? "本命" : "Natal"} | ${cell(chart.chineseDate)} | ${cell(`${zh ? "命主" : "Soul"} ${chart.soul} · ${zh ? "身主" : "Body"} ${chart.body}`)} | ${cell(transformations)} |`,
    ...periodItems.map(([label, item]) => `| ${cell(label)} | ${cell(`${item.heavenlyStem}${item.earthlyBranch}`)} | ${cell(item.name)} | ${cell(item.mutagen.map((star, index) => `${["禄", "权", "科", "忌"][index]} ${star}`).join(" / "))} |`),
  ]
  const themeDefinitions = zh
    ? [
        ["事业", [["命"], ["官禄", "事业"], ["财帛"], ["迁移"]]],
        ["财富", [["命"], ["财帛"], ["田宅"], ["福德"]]],
        ["感情", [["命"], ["夫妻"], ["福德"], ["迁移"]]],
        ["健康结构", [["命"], ["疾厄"], ["福德"]]],
      ] as const
    : [
        ["Career", [["soul", "life"], ["career", "official"], ["wealth", "finance"], ["surface", "travel"]]],
        ["Wealth", [["soul", "life"], ["wealth", "finance"], ["property"], ["spirit", "fortune"]]],
        ["Relationships", [["soul", "life"], ["spouse", "marriage"], ["spirit", "fortune"], ["surface", "travel"]]],
        ["Health structure", [["soul", "life"], ["health", "illness"], ["spirit", "fortune"]]],
      ] as const
  const themes = themeDefinitions.flatMap(([title, aliasGroups]) => {
    const palaces = aliasGroups.flatMap((aliases) => {
      const palace = chart.palaces.find((item) => aliases.some((alias) => item.name.toLowerCase().includes(alias.toLowerCase())))
      return palace ? [palace] : []
    }).filter((palace, index, values) => values.findIndex((item) => item.index === palace.index) === index)
    return [`### ${title}`, ...palaces.map((palace) => `- ${palace.name}：${palace.majorStars.map((star) => `${star.name}${star.brightness ? `(${star.brightness})` : ""}${star.mutagen ? `·化${star.mutagen}` : ""}`).join(" / ") || (zh ? "空宫" : "Empty palace")}`)]
  })
  const rarity = statistics?.rarity_metrics.map((metric) => {
    const display = metric.status === "unsupported" ? (zh ? "暂无基线数据" : "No baseline data") : metric.status === "zero" ? (zh ? "0% · 本参考周期未出现" : "0% · Not observed in this reference") : metric.display_percentage
    return `- ${ziweiMetricMarkdownLabel(metric.feature_id, chart, zh)}：${display}`
  }) ?? []
  const provenance = context?.provenance
  const archiveWarning = context?.archiveMode === "legacy-nonstandard"
    ? (zh ? "> **非标准旧规则档案：此导出保留旧规则与锁定日期，不是统一通行法新版命盘。**" : "> **Legacy nonstandard chart: this export retains legacy rules and a locked date; it is not a new standard-config chart.**")
    : context?.archiveMode === "legacy-static"
      ? (zh ? "> **旧档案静态快照：此导出缺少完整重建参数，日期已锁定。**" : "> **Legacy static snapshot: this export lacks complete rebuild inputs and its date is locked.**")
      : ""
  const provenanceLine = provenance
    ? `> ${zh ? "排盘规则" : "Chart rules"}: ${provenance.configId ?? "legacy"} · ${provenance.algorithm === "default" ? (zh ? "通行法" : "Standard") : (zh ? "中州派" : "Zhongzhou")} · ${provenance.astroType === "heaven" ? (zh ? "天盘" : "Heaven chart") : provenance.astroType === "earth" ? (zh ? "地盘" : "Earth chart") : (zh ? "人盘" : "Human chart")} · ${provenance.yearDivide === "exact" ? (zh ? "立春换年" : "Start-of-Spring year boundary") : (zh ? "正月初一换年" : "Lunar-New-Year boundary")} · ${provenance.dayBoundary === "forward" ? (zh ? "晚子时换日" : "Late-Zi day advance") : (zh ? "晚子时不换日" : "Late-Zi same day")} · ${provenance.calendar === "lunar" ? (zh ? "农历输入" : "Lunar input") : (zh ? "公历输入" : "Solar input")} · ${provenance.fixLeap ? (zh ? "闰月修正开启" : "Leap-month adjustment on") : (zh ? "闰月修正关闭" : "Leap-month adjustment off")}${provenance.calendar === "lunar" ? ` · ${provenance.isLeapMonth ? (zh ? "本月为闰月" : "Leap-month birth") : (zh ? "本月非闰月" : "Non-leap-month birth")}` : ""}`
    : ""
  return [
    `## ${zh ? "命主" : "Chart"}：${title}`,
    "",
    ...consumerMarkdown(context?.consumer, zh),
    `## ${zh ? "紫微斗数" : "Zi Wei Dou Shu"}`,
    "",
    ...summaryTable,
    ...(archiveWarning ? ["", archiveWarning] : []),
    ...(provenanceLine ? ["", provenanceLine] : []),
    "",
    ...palaceTable,
    "",
    `## ${zh ? "四类主题结构" : "Four structural themes"}`,
    "",
    ...themes,
    "",
    `## ${zh ? "运限" : "Periods"}`,
    "",
    ...periodTable,
    ...(rarity.length ? ["", `## ${zh ? "结构出现频率" : "Structural frequency"}`, "", ...rarity, "", `> ${zh ? "出现率只表示这项结构的少见程度，不代表吉凶或人生高低。" : "Incidence only describes how uncommon a structure is; it does not indicate fortune or life quality."}`] : []),
    ...(statistics ? ["", `> ${zh ? "统计基线" : "Baseline"}: ${statistics.baseline.id}`] : []),
  ].join("\n")
}
