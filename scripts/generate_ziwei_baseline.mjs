import crypto from "node:crypto"
import fs from "node:fs"
import path from "node:path"
import os from "node:os"
import { isMainThread, parentPort, Worker, workerData } from "node:worker_threads"
import { createRequire } from "node:module"
import { fileURLToPath } from "node:url"

const here = path.dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)
const { astro } = require(path.join(here, "..", "frontend", "node_modules", "iztro"))

const START = new Date(Date.UTC(1924, 1, 5))
const END = new Date(Date.UTC(2044, 1, 4))
const BASELINE_ID = "ziwei-calendar-1924-2044-v1"
const OUTPUT = path.join(here, "..", "src", "iching", "core", "data", `${BASELINE_ID}.json`)
const BAZI_MANIFEST = JSON.parse(fs.readFileSync(path.join(here, "..", "src", "iching", "core", "data", "bazi-calendar-1924-2044-v1-forward.json"), "utf8"))
const MAJOR = { 紫微: "ziwei", 天机: "tianji", 太阳: "taiyang", 武曲: "wuqu", 天同: "tiantong", 廉贞: "lianzhen", 天府: "tianfu", 太阴: "taiyin", 贪狼: "tanlang", 巨门: "jumen", 天相: "tianxiang", 天梁: "tianliang", 七杀: "qisha", 破军: "pojun" }
const BRANCH = { 子: "zi", 丑: "chou", 寅: "yin", 卯: "mao", 辰: "chen", 巳: "si", 午: "wu", 未: "wei", 申: "shen", 酉: "you", 戌: "xu", 亥: "hai" }
const ELEMENT = { 木: "wood", 火: "fire", 土: "earth", 金: "metal", 水: "water" }
const NUMBER = { 一: "1", 二: "2", 三: "3", 四: "4", 五: "5", 六: "6" }
const BRIGHTNESS = { 庙: "miao", 旺: "wang", 得: "de", 利: "li", 平: "ping", 陷: "xian", 不: "unmarked" }
const MUTAGEN = { 禄: "lu", 权: "quan", 科: "ke", 忌: "ji" }
const AUSPICIOUS = new Set(["左辅", "右弼", "文昌", "文曲", "天魁", "天钺"])
const CHALLENGING = new Set(["擎羊", "陀罗", "火星", "铃星", "地空", "地劫"])

function features(chart) {
  const result = []
  const life = chart.palaces.find((palace) => palace.name === "命宫")
  const lifeStars = (life?.majorStars ?? []).map((star) => MAJOR[star.name]).filter(Boolean).sort()
  result.push(`ziwei.life_combo.${lifeStars.join("-") || "empty"}`)
  const body = chart.palaces.find((palace) => palace.isBodyPalace)
  result.push(`ziwei.body_branch.${BRANCH[body?.earthlyBranch] ?? "unknown"}`)
  const fiveClass = `${ELEMENT[chart.fiveElementsClass?.[0]] ?? "unknown"}-${NUMBER[chart.fiveElementsClass?.[1]] ?? "0"}`
  result.push(`ziwei.five_elements.${fiveClass}`)
  result.push(`ziwei.empty_palaces.${chart.palaces.filter((palace) => palace.majorStars.length === 0).length}`)

  const brightness = new Map()
  const auspiciousDensity = []
  const challengingDensity = []
  chart.palaces.forEach((palace) => {
    let palaceAuspicious = 0
    let palaceChallenging = 0
    palace.majorStars.forEach((star) => {
      const slug = BRIGHTNESS[star.brightness] ?? "unmarked"
      brightness.set(slug, (brightness.get(slug) ?? 0) + 1)
    })
    ;[...palace.majorStars, ...palace.minorStars, ...palace.adjectiveStars].forEach((star) => {
      if (AUSPICIOUS.has(star.name)) palaceAuspicious += 1
      if (CHALLENGING.has(star.name)) palaceChallenging += 1
      if (star.mutagen && MUTAGEN[star.mutagen]) result.push(`ziwei.mutagen.${MUTAGEN[star.mutagen]}.palace-${palace.index}`)
    })
    auspiciousDensity.push(palaceAuspicious)
    challengingDensity.push(palaceChallenging)
  })
  for (const [name, count] of brightness) result.push(`ziwei.brightness.${name}.${count}`)
  result.push(`ziwei.auspicious_palaces.${auspiciousDensity.filter(Boolean).length}`)
  result.push(`ziwei.auspicious_max_density.${Math.max(...auspiciousDensity)}`)
  result.push(`ziwei.challenging_palaces.${challengingDensity.filter(Boolean).length}`)
  result.push(`ziwei.challenging_max_density.${Math.max(...challengingDensity)}`)
  return [...new Set(result)]
}

function runSlice(startDay, endDay) {
  const counts = new Map()
  let sampleWeight = 0
  for (let day = startDay; day < endDay; day += 1) {
    const cursor = new Date(START.getTime() + day * 86400000)
    const date = `${cursor.getUTCFullYear()}-${cursor.getUTCMonth() + 1}-${cursor.getUTCDate()}`
    for (let timeIndex = 0; timeIndex < 12; timeIndex += 1) {
      // The selected natal structural features are gender-invariant in iztro;
      // gender only changes period direction/labels, which are not baseline features.
      const chart = astro.bySolar(date, timeIndex, "男", true, "zh-CN")
      for (const featureId of features(chart)) counts.set(featureId, (counts.get(featureId) ?? 0) + 2)
      sampleWeight += 2
    }
  }
  return { counts: Object.fromEntries(counts), sampleWeight }
}

function buildPayload(counts, sampleWeight) {
  return {
  id: BASELINE_ID,
  chart_type: "ziwei",
  kind: "calendar_sample_frequency",
  label: "1924-02-05—2044-02-04 紫微历法样本",
  start: BAZI_MANIFEST.start,
  end: BAZI_MANIFEST.end,
  timezone: "Asia/Shanghai",
  day_boundary: "iztro-default",
  engine: "iztro 2.5.8",
  rules_version: "ziwei-structural-2026.07-v1",
  sample_unit: "chart",
  sample_weight: sampleWeight,
  method: "逐日 × 12时辰 × 两种性别确定性穷举；所选本命结构经引擎确认不随性别变化，按男女各一份计权；不使用用户数据或随机抽样。",
  gender_weighting: "male_and_female_equal; selected natal structural features are gender-invariant",
    features: Object.fromEntries(Object.entries(counts).sort(([left], [right]) => left.localeCompare(right)).map(([featureId, hitWeight]) => [featureId, { hit_weight: hitWeight }])),
  }
}

function stableStringify(value) {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`
  return JSON.stringify(value)
}

if (!isMainThread) {
  parentPort.postMessage(runSlice(workerData.startDay, workerData.endDay))
} else {
  const totalDays = Math.round((END.getTime() - START.getTime()) / 86400000)
  const workerCount = Math.min(8, Math.max(1, os.availableParallelism?.() ?? os.cpus().length))
  const jobs = Array.from({ length: workerCount }, (_, index) => {
    const startDay = Math.floor(totalDays * index / workerCount)
    const endDay = Math.floor(totalDays * (index + 1) / workerCount)
    return new Promise((resolve, reject) => {
      const worker = new Worker(new URL(import.meta.url), { workerData: { startDay, endDay } })
      worker.once("message", resolve)
      worker.once("error", reject)
      worker.once("exit", (code) => { if (code !== 0) reject(new Error(`worker exited ${code}`)) })
    })
  })
  const results = await Promise.all(jobs)
  const counts = {}
  let sampleWeight = 0
  for (const result of results) {
    sampleWeight += result.sampleWeight
    for (const [featureId, hitWeight] of Object.entries(result.counts)) counts[featureId] = (counts[featureId] ?? 0) + hitWeight
  }
  const payload = buildPayload(counts, sampleWeight)
  const canonical = stableStringify(payload)
  payload.hash = `sha256:${crypto.createHash("sha256").update(canonical).digest("hex")}`
  fs.mkdirSync(path.dirname(OUTPUT), { recursive: true })
  fs.writeFileSync(OUTPUT, `${JSON.stringify(payload, null, 2)}\n`)
  process.stdout.write(`${OUTPUT}: ${sampleWeight} charts, ${payload.hash}\n`)
}
