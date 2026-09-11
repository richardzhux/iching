import { formatFrequency } from "@/lib/frequency-display"
import { ziweiLifeStars, ziweiFeatureIds, ziweiLifeFeatureLabel, ZIWEI_BASELINE_ID } from "@/lib/ziwei-statistics"
import type { ConsumerProfile, MetaphysicsChart, MetaphysicsStatistics, ThemeComparison } from "@/types/api"
import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"
import type { IFunctionalHoroscope } from "iztro/lib/astro/FunctionalHoroscope"
import { canonicalZiweiPalaceName, canonicalZiweiStarName } from "@/lib/ziwei-terms"

type Locale = "en" | "zh"

const cell = (value: string) => value.replaceAll("|", "\\|").replaceAll("\n", "<br>") || "—"

function percentage(value: number, zh: boolean) {
  return formatFrequency(value, zh ? "zh" : "en")
}

function comparisonDisplayLabel(item: ThemeComparison, zh: boolean) {
  if (zh && item.display_label) return item.display_label
  if (!zh) {
    if (item.display_mode === "incidence" || item.comparison_mode === "incidence") {
      return item.hit_percentage != null ? `${percentage(item.hit_percentage, false)}% incidence` : "Incidence recorded"
    }
    if (item.display_mode === "exact_tail") {
      const tail = item.tail_percentage != null ? ` · about ${percentage(item.tail_percentage, false)}% of samples` : ""
      return `${item.display_direction === "low" ? "Distinct lower-side expression" : "Distinct higher-side expression"}${tail}`
    }
    if (item.display_mode === "directional") return item.display_direction === "low" ? "Relatively restrained expression" : "Relatively pronounced expression"
    if (item.display_mode === "reference_zero") return "Not observed in this reference"
    if (item.display_mode === "unavailable" || item.status === "unsupported") return "No comparable baseline"
    if (item.display_mode === "common_value") return "Common range"
  }
  if (item.display_label) return item.display_label
  if (item.comparison_mode === "incidence") {
    const incidence = item.hit_percentage ?? item.exact_percentage
    return incidence != null ? `${zh ? "出现率" : "Incidence"} ${percentage(incidence, zh)}%` : (zh ? "出现率已记录" : "Incidence recorded")
  }
  if (item.status === "unsupported") return zh ? "暂无可比基线" : "No comparable baseline"
  if (item.status === "zero") return zh ? "本参考周期未出现" : "Not observed in this reference"
  return item.semantic_pole || (zh ? "结构位置已记录" : "Structural position recorded")
}

function comparisonMarkdown(item: ThemeComparison, zh: boolean) {
  const value = item.comparison_mode === "incidence"
    ? (item.value ? (zh ? "命中" : "Present") : (zh ? "未命中" : "Absent"))
    : `${item.value}${item.unit || ""}`
  return `- ${item.label} · ${value}：${comparisonDisplayLabel(item, zh)}`
}

export function baziRuleVersionSummary(chart: MetaphysicsChart, locale: Locale, fullDigest = false) {
  const zh = locale === "zh"
  const versions = chart.rule_versions
  if (!versions) {
    return zh ? `排盘规则 ${chart.rules_version}` : `Chart rules ${chart.rules_version}`
  }
  const patternLabel = versions.pattern_bundle === "zzq-shen-canonical-v1"
    ? (zh ? "《子平真诠》沈氏格局规则" : "Shen's Zi Ping pattern rules")
    : versions.pattern_bundle
  const digest = fullDigest ? versions.pattern_digest : versions.pattern_digest.slice(0, 12)
  return zh
    ? `格局依据：${patternLabel} · 版本校验 ${digest} · 历法 ${versions.calendar} · 神煞 ${versions.shensha} · 解读 ${versions.consumer}`
    : `Pattern basis: ${patternLabel} · verification ${digest} · calendar ${versions.calendar} · Shen Sha ${versions.shensha} · interpretation ${versions.consumer}`
}

function consumerMarkdown(consumer: ConsumerProfile | undefined, zh: boolean) {
  if (!consumer?.identity) return []
  const identity = consumer.identity
  const subjectTable = [
    `| ${zh ? "人生主题" : "Life theme"} | ${zh ? "表达路径" : "Expression path"} | ${zh ? "说明" : "Meaning"} |`,
    "| --- | --- | --- |",
    ...consumer.subjects.map((subject) => `| ${cell(subject.label)} | ${cell(subject.path_label || subject.headline || (zh ? "结构路径" : "Structural path"))} | ${cell(subject.path_summary || (subject.drivers ?? []).slice(0, 2).join(" · ") || (zh ? "查看完整命盘" : "See full chart"))} |`),
  ]
  const stages = consumer.life_kline.stages.slice(0, 3).map((stage) => `- ${stage.year}｜**${stage.label}**：${stage.summary || (zh ? "值得关注的阶段" : "A period worth watching")}`)
  const fingerprints = consumer.fingerprints.map((fingerprint) => {
    const incidence = fingerprint.incidence_percentage != null
      ? ` · ${zh ? "出现率" : "incidence"} ${percentage(fingerprint.incidence_percentage, zh)}%`
      : ""
    return `- **${fingerprint.title}**：${fingerprint.detail}（${fingerprint.rarity_label}${incidence}）`
  })
  const combinations = consumer.achievements.map((achievement) => {
    const incidence = achievement.rarity_percentage != null
      ? ` · ${zh ? "出现率" : "incidence"} ${percentage(achievement.rarity_percentage, zh)}%`
      : ""
    const position = achievement.position ? ` · ${zh ? "落位" : "position"} ${achievement.position}` : ""
    return `- **${achievement.title}**｜${achievement.state}${incidence}${position}：${achievement.summary}`
  })
  const seenClaims = new Set<string>()
  const claims = (consumer.claims ?? []).filter((claim) => {
    const key = claim.id || `${claim.title}\u0000${claim.summary}`
    if (seenClaims.has(key)) return false
    seenClaims.add(key)
    return true
  }).map((claim) => {
    const details = [
      ...(claim.evidenceHighlights ?? []),
      ...(claim.comparison?.display ? [claim.comparison.display] : []),
      ...(claim.activation ? [`${claim.activation.layer} · ${claim.activation.ganzhi}${claim.activation.isCurrent ? (zh ? " · 当前" : " · current") : ""}`] : []),
    ].filter(Boolean)
    return `- **${claim.title}**：${claim.summary}${details.length ? `（${details.join(" · ")}）` : ""}`
  })
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
    ...(claims.length ? ["", `### ${zh ? "结构判断" : "Structural findings"}`, "", ...claims] : []),
    ...(fingerprints.length ? ["", `### ${zh ? "较有辨识度的结构" : "Distinctive chart structures"}`, "", ...fingerprints] : []),
    ...(combinations.length ? ["", `### ${zh ? "固定主题组合" : "Fixed topic configurations"}`, "", ...combinations] : []),
    ...(stages.length ? ["", `### ${zh ? "Experimental · 结构活跃阶段" : "Experimental · structural activity stages"}`, "", ...stages] : []),
    "",
  ]
}


export function buildBaziMarkdown(chart: MetaphysicsChart, subjectName: string, locale: Locale) {
  const zh = locale === "zh"
  const statisticsAvailable = !chart.statistics.status || chart.statistics.status === "available"
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
    ...(profile.comparisons ?? []).map((item) => comparisonMarkdown(item, zh)),
    ...profile.evidence.map((item) => `- ${item.evidence_type}｜${item.title}：${item.detail}（${item.source}）`),
  ])
  const legacyFindings = chart.consumer?.claims?.length ? [] : (chart.synthesis?.conclusions ?? []).map((item) => `- **${item.headline}**：${item.body}${item.distribution_context ? `（${item.distribution_context}）` : ""}`)
  return [
    `## ${zh ? "命主" : "Chart"}：${title}`, "", ...consumerMarkdown(chart.consumer, zh), `## ${zh ? "生辰八字" : "BaZi"}`, "", ...table, "", ...facts,
    "", ...dayun,
    "", `## ${zh ? "神煞与历法样本频率" : "Shen Sha and calendar-sample frequency"}`, "", ...shensha,
    "", `> ${zh ? "出现率只表示这项结构在历法样本中的少见程度，不代表吉凶或人生高低。" : "Incidence only describes how uncommon a structure is in calendar samples; it does not indicate fortune or life quality."}`,
    ...(legacyFindings.length ? ["", `## ${zh ? "核心判断" : "Key findings"}`, "", ...legacyFindings] : []),
    "", `## ${zh ? "四主题结构画像" : "Four-theme structure profile"}`, "", ...themes,
    "", `> ${baziRuleVersionSummary(chart, locale, true)} · ${statisticsAvailable ? `${zh ? "统计基线" : "Baseline"} ${chart.statistics.baseline.id}` : (zh ? "历法样本对照暂时不可用" : "Calendar-sample comparisons temporarily unavailable")}`,
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
  const stars = ziweiLifeStars(chart)
  const allowed = new Set(ziweiFeatureIds(chart))
  const compatible = statistics?.status === "available" && statistics.baseline.id === ZIWEI_BASELINE_ID
  const metrics = compatible ? statistics.rarity_metrics.filter((metric) => allowed.has(metric.feature_id)) : []
  return [
    `# ${subjectName.trim() || (zh ? "匿名命盘" : "Anonymous chart")} · ${zh ? "紫微命宫" : "Zi Wei life palace"}`,
    "", `${zh ? "出生日期" : "Birth date"}: ${chart.solarDate}`,
    ...(context?.archiveMode && context.archiveMode !== "standard" ? ["", zh ? "> 旧档案保留原始排盘设置。" : "> Legacy archive retains its original settings."] : []),
    "", `## ${zh ? "命宫主星" : "Life-palace major stars"}`, "",
    ...stars.map((star) => `- ${canonicalZiweiStarName(star.name, locale)} · ${star.brightness_label}`),
    ...(!stars.length ? [zh ? "命宫无十四主星；不借入对宫星，也不代表命运较差。" : "No major stars; opposite-palace stars are not borrowed, and this is not a life grade."] : []),
    "", `## ${zh ? "命宫出现率" : "Life-palace frequencies"}`, "",
    ...(metrics.length ? metrics.map((metric) => `- ${ziweiLifeFeatureLabel(metric.feature_id, chart, locale)}: ${metric.status === "unsupported" ? "—" : metric.display_percentage}`) : [zh ? "暂无兼容的统计参考。" : "No compatible reference available."]),
    "", zh ? "> 1950—2029 年固定历法参考，按时段持续小时加权；不是人口出生分布，出现率不代表吉凶。" : "> Fixed 1950–2029 calendar reference weighted by civil hours; not a population distribution or fortune score.",
    "", `## ${zh ? "原始十二宫" : "Original twelve palaces"}`, "",
    ...chart.palaces.map((palace) => `- ${canonicalZiweiPalaceName(palace.name, locale)} · ${palace.heavenlyStem}${palace.earthlyBranch}: ${palace.majorStars.map((star) => `${canonicalZiweiStarName(star.name, locale)} ${star.brightness || ""}`).join(" / ") || "—"}`),
    "", `${zh ? "所选运限日期" : "Selected period date"}: ${horoscope.solarDate}`,
  ].join("\n")
}
