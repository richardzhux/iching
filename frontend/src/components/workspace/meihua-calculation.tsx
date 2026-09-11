import type { CastingPreview } from "@/types/api"
import type { Locale } from "@/i18n/config"

export function MeihuaCalculation({ cast, locale }: { cast: CastingPreview; locale: Locale }) {
  const p = cast.calculation_inputs
  const original = cast.meihua_mode === "original"
  const zh = locale === "zh"
  const upper = original ? `${p.month} + ${p.day}` : `${p.year_branch} + ${p.lunar_month} + ${p.lunar_day}`
  const lower = original ? `${p.hour} + ${p.minute}` : `${upper} + ${p.hour_branch}`
  const moving = original ? `${p.year} + ${p.month} + ${p.day} + ${p.hour} + ${p.minute}` : lower
  return <div className="meihua-calculation"><p>{original ? (zh ? "公历月、日、时、分取数" : "Gregorian month, day, hour and minute") : (zh ? `年支 ${p.year_branch} · 农历${p.leap_month ? "闰" : ""}${p.lunar_month}月${p.lunar_day}日 · 时支 ${p.hour_branch}` : `Year branch ${p.year_branch} · Lunar ${p.leap_month ? "leap " : ""}${p.lunar_month}/${p.lunar_day} · Hour branch ${p.hour_branch}`)}</p><dl><div><dt>{zh ? "上卦" : "Upper"}</dt><dd>({upper}) mod 8 → {cast.upper_trigram}</dd></div><div><dt>{zh ? "下卦" : "Lower"}</dt><dd>({lower}) mod 8 → {cast.lower_trigram}</dd></div><div><dt>{zh ? "动爻" : "Moving"}</dt><dd>({moving}) mod 6 → {cast.changing_line}</dd></div></dl><p>{zh ? "除八余零作八，除六余零作六。先天卦数：乾1、兑2、离3、震4、巽5、坎6、艮7、坤8。" : "A zero remainder means 8 or 6. Trigram numbers: Heaven 1, Lake 2, Fire 3, Thunder 4, Wind 5, Water 6, Mountain 7, Earth 8."}</p></div>
}
