"use client"

import { useId, useState } from "react"
import { Maximize2 } from "lucide-react"
import { ChartExportButton } from "@/components/tools/chart-export-button"
import { ChartAssetExportButton } from "@/components/tools/chart-asset-export-button"
import { LifeKlineChart } from "@/components/tools/life-kline-chart"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { buildZiweiMarkdown } from "@/lib/chart-markdown"
import { formatFrequency, frequencyLabel } from "@/lib/frequency-display"
import { canonicalZiweiPalaceName, canonicalZiweiStarName, canonicalZiweiTransformationName } from "@/lib/ziwei-terms"
import { buildZiweiLifeKline, lifeFeaturePercentage, type ZiweiConsumerProfile, type ZiweiLifeKline } from "@/lib/ziwei-consumer"
import { ziweiLifeStars, lifeComboId, lifeStateId } from "@/lib/ziwei-statistics"
import type { MetaphysicsStatistics } from "@/types/api"
import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"
import type { IFunctionalHoroscope } from "iztro/lib/astro/FunctionalHoroscope"
import type { IFunctionalPalace } from "iztro/lib/astro/FunctionalPalace"

type Locale = "en" | "zh"
// iztro indexes palaces from 寅; the conventional chart places 寅 at bottom left.
const PALACE_POSITIONS = [[0, 3], [0, 2], [0, 1], [0, 0], [1, 0], [2, 0], [3, 0], [3, 1], [3, 2], [3, 3], [2, 3], [1, 3]] as const
const starName = (value: string, locale: Locale) => canonicalZiweiStarName(value, locale)
const palaceName = (value: string, locale: Locale) => canonicalZiweiPalaceName(value, locale)
const transformationName = (value: string, locale: Locale) => canonicalZiweiTransformationName(value.startsWith("化") ? value : `化${value}`, locale)
const starDetails = (star: IFunctionalPalace["majorStars"][number], locale: Locale) => `${starName(star.name, locale)}${star.brightness ? `（${star.brightness}）` : ""}${star.mutagen ? ` · ${transformationName(star.mutagen, locale)}` : ""}`

export type ZiweiProvenance = {
  configId?: string
  algorithm: "default" | "zhongzhou"
  astroType: "heaven" | "earth" | "human"
  yearDivide: "normal" | "exact"
  dayBoundary: "current" | "forward"
  calendar: "solar" | "lunar"
  fixLeap: boolean
  isLeapMonth: boolean
}

export type ZiweiArchiveMode = "standard" | "legacy-static" | "legacy-nonstandard"
export type ZiweiStatisticsStatus = "loading" | "ready" | "unavailable"

export function ZiweiChartView({ chart, horoscope, horoscopeDate, generatedAt, locale, provenance, subjectName, statistics, statisticsStatus, statisticsError, archiveMode, onHoroscopeDateChange, onCreateStandardCopy }: {
  chart: IFunctionalAstrolabe
  horoscope: IFunctionalHoroscope
  consumer?: ZiweiConsumerProfile
  horoscopeDate: string
  generatedAt: string
  locale: Locale
  provenance: ZiweiProvenance
  subjectName: string
  statistics: MetaphysicsStatistics | null
  statisticsStatus: ZiweiStatisticsStatus
  statisticsError?: string
  archiveMode: ZiweiArchiveMode
  onHoroscopeDateChange: (date: string) => void
  onCreateStandardCopy: () => void
  onCompare?: () => void
}) {
  const exportTargetId = `ziwei-life-${useId().replaceAll(":", "")}`
  const palaceExportTargetId = `ziwei-palaces-${useId().replaceAll(":", "")}`
  const [selectedPalaceIndex, setSelectedPalaceIndex] = useState(() => chart.palaces.find((palace) => palaceName(palace.name, "zh") === "命宫")?.index ?? 0)
  const selectedPalace = chart.palaces.find((palace) => palace.index === selectedPalaceIndex)
  const stars = ziweiLifeStars(chart)
  const names = stars.map((star) => starName(star.name, locale)).join(" × ") || (locale === "zh" ? "命宫无十四主星" : "No major stars in the life palace")
  const states = stars.map((star) => `${starName(star.name, locale)}（${star.brightness_label}）`).join(" × ")
  const stats = archiveMode === "standard" && statisticsStatus === "ready" ? statistics : null
  const frequency = (id: string) => { const value = lifeFeaturePercentage(stats, id); return value === null ? "—" : `${formatFrequency(value, locale)}% · ${frequencyLabel(value, locale)}` }
  const markdown = buildZiweiMarkdown(chart, horoscope, subjectName, locale, stats ?? undefined, { archiveMode, provenance })
  return <section className="chart-report autumn-chart-workspace min-w-0 space-y-7" aria-label={locale === "zh" ? "紫微斗数结果" : "Zi Wei result"}>
    <div className="flex justify-end"><ChartExportButton targetId={exportTargetId} markdown={markdown} label={locale === "zh" ? "导出命宫" : "Export life palace"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "导出失败" : "Export failed"} safeBaseFilename={`ziwei-life-${horoscopeDate}`} /></div>
    <ZiweiArchiveBanner archiveMode={archiveMode} locale={locale} onCreateStandardCopy={onCreateStandardCopy} />
    <article id={exportTargetId} className="space-y-6 rounded-3xl border border-border/60 bg-surface p-5 sm:p-8">
      <header>
        <p className="kicker">{locale === "zh" ? "紫微斗数 · 你的命宫主星" : "ZI WEI · YOUR LIFE-PALACE STARS"}</p>
        <h2 className="mt-3 text-3xl font-semibold">{names}</h2>
        {subjectName ? <p className="mt-2 text-sm">{subjectName}</p> : null}
        {stars.length ? <p className="mt-4 text-lg font-medium text-primary">{states}</p> : <p className="mt-4 text-sm leading-7 text-muted-foreground">{locale === "zh" ? "命宫未落入十四主星，传统上称为空宫。可在下方十二宫命盘继续查看其他星曜与宫位。" : "A life palace with no major stars is traditionally called an empty palace. Explore its other stars and placements in the twelve-palace chart below."}</p>}
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">{locale === "zh" ? "庙、旺等标签是传统排盘对星曜在所处宫位状态的描述，统称“亮度”。解读时还要结合其他星曜与四化，不能只凭一颗星或一个标签判断吉凶。" : "Labels such as 庙 and 旺 describe a star’s traditional state in its palace, called “brightness.” They are read alongside the other stars and transformations; a single label does not determine fortune."}</p>
      </header>
      <details className="border-t border-border/60 pt-4">
        <summary className="cursor-pointer text-sm font-semibold">{locale === "zh" ? "查看命宫出现率与统计口径" : "View life-palace frequencies and reference"}</summary>
        <div className="mt-4 space-y-4">
          <dl className="grid gap-4 sm:grid-cols-2">
            <div><dt className="text-sm text-muted-foreground">{locale === "zh" ? "主星组合出现率" : "Combination frequency"}</dt><dd className="mt-1 font-semibold text-primary">{frequency(lifeComboId(stars))}</dd></div>
            {stars.length ? <div><dt className="text-sm text-muted-foreground">{locale === "zh" ? "组合与亮度联合出现率" : "Combination + brightness frequency"}</dt><dd className="mt-1 font-semibold text-primary">{frequency(lifeStateId(stars))}</dd></div> : null}
          </dl>
          {stars.length ? <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-border"><th className="py-3">{locale === "zh" ? "命宫主星" : "Major star"}</th><th>{locale === "zh" ? "亮度" : "Brightness"}</th><th>{locale === "zh" ? "该星在命宫且为此亮度" : "Star in life palace at this brightness"}</th></tr></thead><tbody>{stars.map((star) => <tr key={star.id} className="border-b border-border/50"><td className="py-3 font-semibold">{starName(star.name, locale)}</td><td>{star.brightness_label}</td><td>{frequency(`ziwei.life_star.${star.id}.${star.brightness}`)}</td></tr>)}</tbody></table></div> : null}
          {statisticsStatus === "loading" ? <p role="status" className="text-sm text-muted-foreground">{locale === "zh" ? "正在加载参考频率…" : "Loading reference frequencies…"}</p> : !stats ? <p className="text-sm text-muted-foreground">{statisticsError || (locale === "zh" ? "当前没有兼容的频率参考；命宫事实保留，百分比留空。" : "No compatible reference is available. Chart facts remain; percentages stay blank.")}</p> : null}
          <p className="text-sm leading-7 text-muted-foreground">{locale === "zh" ? "1950—2029 年固定历法参考。逐日按早子、晚子各 1 小时，其余时段各 2 小时加权。仅统计命宫内实际落入的十四主星；排列先后不改变组合，空宫不借入对宫星。亮度为庙、旺、得、利、平、不、陷；缺失状态记未标明。所有百分比分母均为完整参考时间，联合出现率直接计数，不相乘。SSR ≤5%，SR >5% 且 ≤10%，R >10% 且 ≤20%；仅表示频率，不表示吉凶。" : "Fixed 1950–2029 calendar reference. Early and late Zi each receive one hour; other slots receive two. Only the fourteen major stars actually in the life palace are counted. Order does not change the combination; opposite-palace stars are not borrowed. Brightness states: 庙, 旺, 得, 利, 平, 不, 陷; missing values stay unknown. All percentages use the full reference duration. Joint events are counted directly. SSR ≤5%, SR >5–10%, R >10–20%; frequency is not fortune."}</p>
          {stats ? <p className="text-xs text-muted-foreground">{stats.baseline.label} · {stats.baseline.sample_weight?.toLocaleString()} {locale === "zh" ? "小时权重" : "weighted hours"}</p> : null}
        </div>
      </details>
    </article>
    <details className="rounded-3xl border border-border/60 bg-surface p-5 sm:p-7"><summary className="cursor-pointer text-xl font-semibold">{locale === "zh" ? "原始十二宫命盘" : "Original twelve-palace chart"}</summary><div className="mt-5 flex flex-wrap gap-2"><FullChartDialog chart={chart} horoscope={horoscope} locale={locale} /><ChartAssetExportButton targetId={palaceExportTargetId} label={locale === "zh" ? "导出十二宫" : "Export palaces"} loadingLabel="…" errorLabel={locale === "zh" ? "导出失败" : "Export failed"} safeBaseFilename={`ziwei-palaces-${horoscopeDate}`} /></div><div className="mt-5 md:hidden"><MobilePalaceRail chart={chart} horoscope={horoscope} locale={locale} selectedPalaceIndex={selectedPalaceIndex} onSelect={setSelectedPalaceIndex} /></div><div className="mt-5 hidden overflow-x-auto md:block"><ZiweiPalaceChart chart={chart} horoscope={horoscope} locale={locale} interactive selectedPalaceIndex={selectedPalaceIndex} onSelect={setSelectedPalaceIndex} /></div>{selectedPalace ? <SelectedPalaceDetail selectedPalace={selectedPalace} locale={locale} /> : null}<ZiweiPeriodPanel chart={chart} horoscope={horoscope} selectedDate={horoscopeDate} onSelectedDateChange={onHoroscopeDateChange} locked={archiveMode !== "standard"} locale={locale} /><p className="mt-4 text-xs text-muted-foreground">{provenance.configId} · {generatedAt}</p></details>
    {archiveMode === "standard" ? <ZiweiExperimental key={generatedAt} chart={chart} locale={locale} /> : null}
    <div aria-hidden="true" inert className="chart-export-stage"><article id={palaceExportTargetId} className="chart-share-canvas chart-export-canvas"><ZiweiPalaceChart chart={chart} horoscope={horoscope} locale={locale} interactive={false} /></article></div>
  </section>
}

function ZiweiExperimental({ chart, locale }: { chart: IFunctionalAstrolabe; locale: Locale }) {
  const [series, setSeries] = useState<ZiweiLifeKline | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  function expand(open: boolean) {
    if (!open || series || loading) return
    setLoading(true)
    window.setTimeout(() => { try { setSeries(buildZiweiLifeKline(chart)) } catch { setError(true) } finally { setLoading(false) } }, 0)
  }
  return <details className="rounded-3xl border border-dashed border-primary/40 bg-surface p-5 sm:p-7" onToggle={(event) => expand(event.currentTarget.open)}><summary className="cursor-pointer font-semibold">Experimental · {locale === "zh" ? "命宫主星活跃度走势" : "Life-palace activity"}</summary><p className="mt-4 text-sm leading-7 text-muted-foreground">{locale === "zh" ? "实验功能：只计大限、流年、流月四化触及本命命宫主星的次数，每项同权，不分吉凶。每月取 15 日，跳过出生前的采样；100 对应个人参考跨度内的月度平均活动量，曲线经过压缩，不是概率或人生评分。" : "Experimental: counts period transformations touching natal life-palace major stars equally, without positive or negative grades. Each month is sampled on the 15th, excluding dates before birth. The compressed index is centered on the personal monthly mean, not a probability or life rating."}</p>{loading ? <p role="status" className="mt-4">{locale === "zh" ? "正在计算个人参考跨度…" : "Calculating the personal reference…"}</p> : null}{error ? <p role="alert" className="mt-4">{locale === "zh" ? "该档案暂不能生成完整实验曲线。" : "This archive cannot produce a complete experimental series."}</p> : null}{series ? <div className="mt-5"><LifeKlineChart lifeKline={series} locale={locale} currentYear={new Date().getFullYear()} /></div> : null}</details>
}

function ZiweiArchiveBanner({ archiveMode, locale, onCreateStandardCopy }: { archiveMode: ZiweiArchiveMode; locale: Locale; onCreateStandardCopy: () => void }) {
  if (archiveMode === "standard") return null
  const nonstandard = archiveMode === "legacy-nonstandard"
  return (
    <aside data-export-exclude className="flex flex-col gap-3 rounded-xl border border-border/60 bg-surface px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-semibold">{nonstandard ? (locale === "zh" ? "非标准旧规则档案" : "Legacy nonstandard chart") : (locale === "zh" ? "旧档案静态快照" : "Legacy static snapshot")}</p>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">{nonstandard
          ? (locale === "zh" ? "此档案使用旧规则，以只读快照保留；日期与频率统计不会重算。" : "This archive used legacy rules and is preserved read-only; its date and frequency statistics are not recalculated.")
          : (locale === "zh" ? "此档案缺少完整标准化输入；当前日期锁定，仅展示保存时的结果。" : "This archive lacks complete normalized inputs. Its date is locked and only the saved result is shown.")}</p>
      </div>
      {nonstandard ? <Button type="button" variant="outline" onClick={onCreateStandardCopy}>{locale === "zh" ? "按统一规则创建副本" : "Create standard copy"}</Button> : null}
    </aside>
  )
}

function FullChartDialog({ chart, horoscope, locale }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; locale: Locale }) {
  return <Dialog><DialogTrigger asChild><Button type="button" variant="outline"><Maximize2 aria-hidden="true" className="mr-2 size-4" />{locale === "zh" ? "全盘模式" : "Full chart"}</Button></DialogTrigger><DialogContent className="h-[94dvh] max-w-[96vw] overflow-auto p-4 sm:max-w-[96vw]"><DialogHeader><DialogTitle>{locale === "zh" ? "紫微斗数全盘" : "Full Zi Wei chart"}</DialogTitle><DialogDescription>{locale === "zh" ? "适合桌面、平板横屏或投屏查看。" : "Optimized for desktop, landscape tablet, or presentation."}</DialogDescription></DialogHeader><div className="min-w-[72rem]"><ZiweiPalaceChart chart={chart} horoscope={horoscope} locale={locale} interactive={false} /></div></DialogContent></Dialog>
}

function MobilePalaceRail({ chart, horoscope, locale, selectedPalaceIndex, onSelect }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; locale: Locale; selectedPalaceIndex?: number; onSelect: (index: number) => void }) {
  return <div className="grid grid-cols-2 gap-2">{chart.palaces.slice(0, 12).map((palace) => { const selected = palace.index === selectedPalaceIndex; const decadal = palace.index === horoscope.decadal.index; const yearly = palace.index === horoscope.yearly.index; return <button type="button" key={`${palace.name}-${palace.index}`} onClick={() => onSelect(palace.index)} aria-pressed={selected} className={`min-h-32 rounded-xl border p-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${selected ? "border-primary bg-primary/10" : "border-border/55 bg-surface"}`}><span className="flex items-start justify-between gap-2"><strong>{palaceName(palace.name, locale)}{palace.isBodyPalace ? ` · ${locale === "zh" ? "身" : "Body"}` : ""}</strong><span className="text-xs text-muted-foreground">{palace.heavenlyStem}{palace.earthlyBranch}</span></span><span className="mt-2 flex flex-wrap gap-1">{decadal ? <small className="rounded-full bg-primary/12 px-1.5 py-0.5 font-semibold text-primary">{locale === "zh" ? "大限" : "Decadal"}</small> : null}{yearly ? <small className="rounded-full bg-primary/12 px-1.5 py-0.5 font-semibold text-primary">{locale === "zh" ? "流年" : "Year"}</small> : null}</span><span className="mt-2 block text-sm font-semibold text-primary">{palace.majorStars.map((star) => starName(star.name, locale)).join(" · ") || (locale === "zh" ? "空宫" : "Empty")}</span><AuxiliaryStars palace={palace} locale={locale} /></button> })}</div>
}

function ZiweiPeriodPanel({ chart, horoscope, selectedDate, onSelectedDateChange, locked, locale, showDateControl = true }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; selectedDate: string; onSelectedDateChange: (date: string) => void; locked: boolean; locale: Locale; showDateControl?: boolean }) {
  const items = [
    { label: locale === "zh" ? "大限" : "Decadal", ...horoscope.decadal },
    { label: locale === "zh" ? "流年" : "Yearly", ...horoscope.yearly },
    { label: locale === "zh" ? "流月" : "Monthly", ...horoscope.monthly },
    { label: locale === "zh" ? "流日" : "Daily", ...horoscope.daily },
    { label: locale === "zh" ? "流时 · 00:00" : "Hourly · 00:00", ...horoscope.hourly },
  ]
  return <div className="mt-5 space-y-5">
    {showDateControl ? <div className="max-w-xs">
      <label htmlFor="ziwei-period-date" className="text-xs font-semibold text-muted-foreground">{locale === "zh" ? "查看日期" : "Horoscope date"}</label>
      <Input id="ziwei-period-date" className="mt-2" type="date" min="1900-01-31" max="2100-12-31" value={selectedDate} disabled={locked} onChange={(event) => onSelectedDateChange(event.target.value)} />
      {locked ? <p className="mt-2 text-xs text-muted-foreground">{locale === "zh" ? "静态档案日期已锁定" : "Date locked for static archive"}</p> : null}
    </div> : null}
    <div className="grid gap-3 lg:grid-cols-5">{items.map((item) => {
      const natalPalace = chart.palaces.find((palace) => palace.index === item.index)
      return <article key={item.label} className="rounded-xl border border-border/50 bg-surface p-4">
        <p className="text-xs font-semibold text-muted-foreground">{item.label}</p>
        <p className="mt-2 text-lg font-semibold">{item.heavenlyStem}{item.earthlyBranch}</p>
        <p className="mt-2 text-sm leading-6">{natalPalace
          ? (locale === "zh" ? `本层命宫落本命${palaceName(natalPalace.name, locale)}` : `Life palace in natal ${palaceName(natalPalace.name, locale)}`)
          : (locale === "zh" ? "本层命宫未标明" : "Life-palace placement unavailable")}</p>
        {item.mutagen?.length ? <ul className="mt-3 space-y-1 text-xs leading-5 text-muted-foreground">{item.mutagen.map((star, index) => <li key={`${star}-${index}`}>{canonicalZiweiTransformationName(["化禄", "化权", "化科", "化忌"][index], locale)} · {starName(star, locale)}</li>)}</ul> : <p className="mt-3 text-xs text-muted-foreground">{locale === "zh" ? "本层无新增四化" : "No new transformation in this layer"}</p>}
      </article>
    })}</div>
    <p className="text-sm leading-6 text-muted-foreground">{locale === "zh" ? "更改日期，可对照各层命宫落在本命哪一宫，以及对应的四化。" : "Change the date to compare each period’s life-palace placement in the natal chart and its four transformations."}</p>
    <details><summary className="cursor-pointer text-sm font-semibold text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">{locale === "zh" ? "这些运限怎么看" : "How to read these periods"}</summary><p className="mt-3 text-xs leading-5 text-muted-foreground">{locale === "zh" ? "大限、流年、流月、流日、流时分别观察十年、一年、一月、一天和一个时辰。每层的命宫都可对应到本命十二宫，四化依次列出化禄、化权、化科、化忌的星曜。当前日期选择器按当日 00:00 计算流时。" : "The layers cover a decade, year, month, day, and two-hour period. Each period’s life palace is located within the natal twelve palaces. The four transformations list 化禄, 化权, 化科, and 化忌 and their stars. The date selector computes the hourly layer at 00:00."}</p></details>
  </div>
}

function ZiweiPalaceChart({ chart, horoscope, locale, interactive, selectedPalaceIndex, onSelect }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; locale: Locale; interactive: boolean; selectedPalaceIndex?: number; onSelect?: (index: number) => void }) {
  return (
    <div className={`grid grid-cols-4 grid-rows-4 gap-px overflow-hidden border border-border/60 bg-border/60 ${interactive ? "autumn-palace-grid min-h-[42rem] min-w-[42rem]" : "h-[760px] w-full"}`}>
      {chart.palaces.slice(0, 12).map((palace) => {
        const isSelected = selectedPalaceIndex === palace.index
        const isDecadal = horoscope?.decadal.index === palace.index
        const isYearly = horoscope?.yearly.index === palace.index
        if (interactive) {
          return <PalaceButton key={`${palace.name}-${palace.earthlyBranch}`} palace={palace} position={PALACE_POSITIONS[palace.index]} locale={locale} isSelected={isSelected} isDecadal={isDecadal} isYearly={isYearly} onSelect={() => onSelect?.(palace.index)} />
        }
        return (
          <section key={`${palace.name}-${palace.earthlyBranch}`} style={{ gridColumnStart: PALACE_POSITIONS[palace.index][0] + 1, gridRowStart: PALACE_POSITIONS[palace.index][1] + 1 }} className="bg-surface p-3.5">
            <div className="flex items-start justify-between gap-2"><strong className="text-base">{palaceName(palace.name, locale)}{palace.isBodyPalace ? ` · ${locale === "zh" ? "身" : "Body"}` : ""}</strong><span className="text-sm text-muted-foreground">{palace.heavenlyStem}{palace.earthlyBranch}</span></div>
            <div className="mt-2 flex flex-wrap gap-x-2 gap-y-1 text-sm leading-5">{palace.majorStars.length ? palace.majorStars.map((star, starIndex) => <span key={`${star.name}-${starIndex}`} className="font-semibold text-primary">{starDetails(star, locale)}</span>) : <span className="text-muted-foreground">{locale === "zh" ? "空宫" : "Empty palace"}</span>}</div>
            <AuxiliaryStars palace={palace} locale={locale} />
            <p className="mt-2 text-xs text-muted-foreground">{isDecadal ? `${locale === "zh" ? "大限" : "Decadal"} · ` : ""}{isYearly ? `${locale === "zh" ? "流年" : "Annual"} · ` : ""}{palace.changsheng12} · {palace.decadal.range[0]}–{palace.decadal.range[1]}</p>
          </section>
        )
      })}
      <div className="col-start-2 col-end-4 row-start-2 row-end-4 flex flex-col items-center justify-center bg-primary/[0.07] p-6 text-center">
        <p className="text-2xl font-semibold">{locale === "zh" ? "十二宫命盘" : "Twelve-palace chart"}</p>
        <p className="mt-4 text-xs font-semibold text-muted-foreground">{locale === "zh" ? "出生日期 · 阳历" : "Birth date · solar calendar"}</p>
        <p className="mt-1 text-base font-medium">{chart.solarDate}</p>
        <p className="mt-1 text-sm text-muted-foreground">{locale === "zh" ? "出生农历" : "Lunar birth date"} · {chart.lunarDate}</p>
        <p className="mt-2 text-sm">{[chart.gender, chart.time, chart.timeRange, chart.fiveElementsClass].filter(Boolean).join(" · ")}</p>
        <div className="mt-4 border-t border-primary/15 pt-3">
          <p className="text-xs font-semibold text-muted-foreground">{locale === "zh" ? "查看运限日期 · 阳历" : "Selected period date · solar calendar"}</p>
          <p className="mt-1 text-sm">{horoscope.solarDate}</p>
          <p className="mt-1 text-xs text-muted-foreground">{locale === "zh" ? "运限农历" : "Lunar period date"} · {horoscope.lunarDate}</p>
        </div>
      </div>
    </div>
  )
}

function AuxiliaryStars({ palace, locale }: { palace: IFunctionalPalace; locale: Locale }) {
  const stars = [...palace.minorStars, ...palace.adjectiveStars]
  const transformed = stars.filter((star) => star.mutagen)
  const others = stars.filter((star) => !star.mutagen)
  return <span className="mt-2 block text-xs leading-5 text-muted-foreground">
    {transformed.length ? <span className="block font-medium text-primary">{transformed.map((star) => starDetails(star, locale)).join(" · ")}</span> : null}
    {others.length ? <span className="line-clamp-2 block">{others.map((star) => starName(star.name, locale)).join(" · ")}</span> : null}
    {!stars.length ? "—" : null}
  </span>
}

function PalaceButton({ palace, position, locale, isSelected, isDecadal, isYearly, onSelect }: { palace: IFunctionalPalace; position: readonly [number, number]; locale: Locale; isSelected: boolean; isDecadal: boolean; isYearly: boolean; onSelect: () => void }) {
  const palaceLabel = `${palaceName(palace.name, locale)} ${palace.heavenlyStem}${palace.earthlyBranch}${isDecadal ? `, ${locale === "zh" ? "大限" : "Decadal period"}` : ""}${isYearly ? `, ${locale === "zh" ? "流年" : "Annual period"}` : ""}`
  return (
    <button
      type="button"
      style={{ gridColumnStart: position[0] + 1, gridRowStart: position[1] + 1 }}
      aria-label={palaceLabel}
      aria-pressed={isSelected}
      onClick={onSelect}
      className={`autumn-palace-node min-w-0 p-3.5 text-left transition focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${isSelected ? "bg-primary/12 shadow-[inset_0_0_0_2px_var(--primary)]" : "bg-surface hover:bg-primary/[0.055]"}`}
    >
      <span className="flex items-start justify-between gap-2"><strong className="text-base">{palaceName(palace.name, locale)}{palace.isBodyPalace ? ` · ${locale === "zh" ? "身" : "Body"}` : ""}</strong><span className="text-sm text-muted-foreground">{palace.heavenlyStem}{palace.earthlyBranch}</span></span>
      <span className="mt-2 flex flex-wrap gap-1">
        {isDecadal ? <span className="rounded border border-primary/40 bg-primary/10 px-1.5 py-0.5 text-[0.65rem] font-semibold">{locale === "zh" ? "大限" : "Decadal"}</span> : null}
        {isYearly ? <span className="rounded border border-primary/40 bg-primary/10 px-1.5 py-0.5 text-[0.65rem] font-semibold">{locale === "zh" ? "流年" : "Annual"}</span> : null}
      </span>
      <span className="mt-2 flex flex-wrap gap-x-2 gap-y-1">{palace.majorStars.length ? palace.majorStars.map((star, index) => <span key={`${star.name}-${index}`} className="text-sm font-semibold text-primary">{starDetails(star, locale)}</span>) : <span className="text-sm text-muted-foreground">{locale === "zh" ? "空宫" : "Empty palace"}</span>}</span>
      <AuxiliaryStars palace={palace} locale={locale} />
      <span className="mt-2 block text-xs text-muted-foreground">{palace.changsheng12} · {palace.decadal.range[0]}–{palace.decadal.range[1]}</span>
    </button>
  )
}

function SelectedPalaceDetail({ selectedPalace, locale }: { selectedPalace: IFunctionalPalace; locale: Locale }) {
  return (
    <section aria-labelledby="selected-palace-title" className="autumn-node-detail border-t border-border/60 pt-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{locale === "zh" ? "所选宫位" : "Selected palace"}</p><h2 id="selected-palace-title" className="mt-1 text-xl font-semibold">{palaceName(selectedPalace.name, locale)}{selectedPalace.isBodyPalace ? ` · ${locale === "zh" ? "身宫" : "Body palace"}` : ""}</h2></div>
        <p className="text-sm font-semibold">{selectedPalace.heavenlyStem}{selectedPalace.earthlyBranch}</p>
      </div>
      <div className="mt-4 grid divide-y divide-border/60 md:grid-cols-3 md:divide-x md:divide-y-0">
        <StarGroup title={locale === "zh" ? "主星" : "Major stars"} stars={selectedPalace.majorStars} locale={locale} emptyLabel={locale === "zh" ? "空宫（无主星）" : "Empty palace (no major stars)"} />
        <StarGroup title={locale === "zh" ? "辅星" : "Minor stars"} stars={selectedPalace.minorStars} locale={locale} />
        <StarGroup title={locale === "zh" ? "杂耀" : "Adjective stars"} stars={selectedPalace.adjectiveStars} locale={locale} />
      </div>
      <div className="mt-2 grid gap-2 border-t border-border/60 pt-4 text-xs text-muted-foreground sm:grid-cols-2">
        <p>{locale === "zh" ? "长生" : "Changsheng"}: {selectedPalace.changsheng12}</p>
        <p>{locale === "zh" ? "大限年龄" : "Decadal ages"}: {selectedPalace.decadal.range[0]}–{selectedPalace.decadal.range[1]}</p>
        <p>{locale === "zh" ? "博士十二神" : "Scholar-cycle star"}: {starName(selectedPalace.boshi12, locale)}</p>
        <p>{locale === "zh" ? "将前十二神" : "General-cycle star"}: {starName(selectedPalace.jiangqian12, locale)}</p>
        <p>{locale === "zh" ? "岁前十二神" : "Annual-cycle star"}: {starName(selectedPalace.suiqian12, locale)}</p>
        <p>{locale === "zh" ? "小限年龄" : "Minor-period ages"}: {selectedPalace.ages.join(" · ")}</p>
      </div>
    </section>
  )
}

function StarGroup({ title, stars, locale, emptyLabel }: { title: string; stars: IFunctionalPalace["majorStars"]; locale: Locale; emptyLabel?: string }) {
  return (
    <section className="py-4 md:px-4 md:first:pl-0 md:last:pr-0">
      <h3 className="text-sm font-semibold">{title}</h3>
      {stars.length ? <ul className="mt-2 divide-y divide-border/50">{stars.map((star, index) => <li key={`${star.name}-${index}`} className="py-2 text-sm"><span className="font-medium">{starName(star.name, locale)}</span><span className="ml-2 text-xs text-muted-foreground">{star.mutagen ? transformationName(star.mutagen, locale) : ""}{star.mutagen && star.brightness ? " · " : ""}{star.brightness ? `${locale === "zh" ? "亮度" : "Brightness"} ${star.brightness}` : ""}</span></li>)}</ul> : <p className="mt-2 text-xs text-muted-foreground">{emptyLabel || (locale === "zh" ? "无" : "None")}</p>}
    </section>
  )
}
