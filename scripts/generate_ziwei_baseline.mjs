import crypto from "node:crypto"
import fs from "node:fs"
import path from "node:path"
import os from "node:os"
import { isMainThread, parentPort, Worker, workerData } from "node:worker_threads"
import { createRequire } from "node:module"
import { fileURLToPath } from "node:url"

const here = path.dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)

const START = new Date(Date.UTC(1924, 1, 5))
const END = new Date(Date.UTC(2044, 1, 4))
const BASELINE_ID = "ziwei-calendar-1924-2044-v1"
const OUTPUT = path.join(here, "..", "src", "iching", "core", "data", `${BASELINE_ID}.json`)
const SCHEMA_VERSION = 3
const CONFIG_ID = "ziwei-standard-v1"
const RULES_VERSION = "ziwei-structural-2026.07-v2.1"
const CONSUMER_RULES_VERSION = "ziwei-consumer-c1"
const TIME_INDEX_WEIGHTS = Object.freeze([1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1])
const TIME_INDEX_LABELS = Object.freeze(["早子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "晚子"])
const SCORE_KEYS = Object.freeze(["overall", "career", "wealth", "relationship", "health"])
const REGISTRY_DESCRIPTOR = {
  rules_version: RULES_VERSION,
  consumer_rules_version: CONSUMER_RULES_VERSION,
  encoding_version: 1,
  feature_families: [
    "life_combo",
    "body_branch",
    "five_elements",
    "empty_palaces",
    "brightness",
    "mutagen_palace_index",
    "auspicious_palaces",
    "auspicious_max_density",
    "challenging_palaces",
    "challenging_max_density",
    "achievement",
    "archetype",
    "consumer_score_histogram",
    "structural_family",
  ],
}
const MAJOR = { 紫微: "ziwei", 天机: "tianji", 太阳: "taiyang", 武曲: "wuqu", 天同: "tiantong", 廉贞: "lianzhen", 天府: "tianfu", 太阴: "taiyin", 贪狼: "tanlang", 巨门: "jumen", 天相: "tianxiang", 天梁: "tianliang", 七杀: "qisha", 破军: "pojun" }
const BRANCH = { 子: "zi", 丑: "chou", 寅: "yin", 卯: "mao", 辰: "chen", 巳: "si", 午: "wu", 未: "wei", 申: "shen", 酉: "you", 戌: "xu", 亥: "hai" }
const ELEMENT = { 木: "wood", 火: "fire", 土: "earth", 金: "metal", 水: "water" }
const NUMBER = { 一: "1", 二: "2", 三: "3", 四: "4", 五: "5", 六: "6" }
const BRIGHTNESS = { 庙: "miao", 旺: "wang", 得: "de", 利: "li", 平: "ping", 陷: "xian", 不: "unmarked" }
const MUTAGEN = { 禄: "lu", 权: "quan", 科: "ke", 忌: "ji" }
const AUSPICIOUS = new Set(["左辅", "右弼", "文昌", "文曲", "天魁", "天钺"])
const CHALLENGING = new Set(["擎羊", "陀罗", "火星", "铃星", "地空", "地劫"])
const ACHIEVEMENT_IDS = Object.freeze([
  "ziwei-tianfu", "sun-moon", "left-right", "chang-qu", "kui-yue", "sha-po-lang",
  "three-positive-transformations", "six-aids-network", "life-body-aligned",
  "main-axis-obstacle", "life-axis-defined",
])
const MAJOR_LABEL_BY_SLUG = Object.fromEntries(Object.entries(MAJOR).map(([label, slug]) => [slug, label]))

function supportedFeatureCatalog() {
  const ids = new Set()
  const majorSlugs = Object.values(MAJOR).sort()
  ids.add("ziwei.life_combo.empty")
  for (const star of majorSlugs) ids.add(`ziwei.life_combo.${star}`)
  for (let left = 0; left < majorSlugs.length; left += 1) {
    for (let right = left + 1; right < majorSlugs.length; right += 1) {
      ids.add(`ziwei.life_combo.${[majorSlugs[left], majorSlugs[right]].sort().join("-")}`)
    }
  }
  for (const branch of Object.values(BRANCH)) ids.add(`ziwei.body_branch.${branch}`)
  for (const element of Object.values(ELEMENT)) {
    for (const value of Object.values(NUMBER)) ids.add(`ziwei.five_elements.${element}-${value}`)
  }
  for (let count = 0; count <= 12; count += 1) {
    ids.add(`ziwei.empty_palaces.${count}`)
    ids.add(`ziwei.auspicious_palaces.${count}`)
    ids.add(`ziwei.challenging_palaces.${count}`)
  }
  for (const brightness of Object.values(BRIGHTNESS)) {
    for (let count = 0; count <= 14; count += 1) ids.add(`ziwei.brightness.${brightness}.${count}`)
  }
  for (const mutagen of Object.values(MUTAGEN)) {
    for (let palace = 0; palace < 12; palace += 1) ids.add(`ziwei.mutagen.${mutagen}.palace-${palace}`)
  }
  for (let count = 0; count <= 6; count += 1) ids.add(`ziwei.auspicious_max_density.${count}`)
  for (let count = 0; count <= 6; count += 1) ids.add(`ziwei.challenging_max_density.${count}`)
  for (const achievementId of ACHIEVEMENT_IDS) ids.add(`ziwei.achievement.${achievementId}`)
  return ids
}

let astroEngine
let consumerScoreEngine

function astro() {
  if (!astroEngine) {
    ;({ astro: astroEngine } = require(path.join(here, "..", "frontend", "node_modules", "iztro")))
  }
  return astroEngine
}

async function consumerScorer() {
  if (!consumerScoreEngine) {
    // Keep the production bundle free of baseline-generation code while still
    // using the exact same score function. TypeScript is already a frontend
    // dev dependency; transpilation happens once per worker, never at runtime.
    const ts = require(path.join(here, "..", "frontend", "node_modules", "typescript"))
    const source = fs.readFileSync(path.join(here, "..", "frontend", "src", "lib", "ziwei-consumer.ts"), "utf8")
    const compiled = ts.transpileModule(source, {
      compilerOptions: {
        target: ts.ScriptTarget.ES2022,
        module: ts.ModuleKind.ES2022,
        importsNotUsedAsValues: ts.ImportsNotUsedAsValues.Remove,
      },
    }).outputText
    const moduleUrl = `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
    const consumerModule = await import(moduleUrl)
    if (consumerModule.ZIWEI_CONSUMER_RULES_VERSION !== CONSUMER_RULES_VERSION) {
      throw new Error(`consumer rules mismatch: ${consumerModule.ZIWEI_CONSUMER_RULES_VERSION}`)
    }
    consumerScoreEngine = consumerModule.computeZiweiNatalConsumerScores
  }
  return consumerScoreEngine
}

function emptyScoreHistograms() {
  return Object.fromEntries(SCORE_KEYS.map((key) => [key, {}]))
}

function addHistogramValue(histogram, value, weight) {
  const bin = String(value)
  histogram[bin] = (histogram[bin] ?? 0) + weight
}

function mergeScoreHistograms(target, source) {
  for (const key of SCORE_KEYS) {
    for (const [bin, weight] of Object.entries(source[key] ?? {})) {
      target[key][bin] = (target[key][bin] ?? 0) + weight
    }
  }
}

function addRepresentative(target, key, label) {
  target[key] ??= []
  if (target[key].length < 3 && !target[key].includes(label)) target[key].push(label)
}

function mergeRepresentatives(target, source) {
  for (const [key, labels] of Object.entries(source)) {
    for (const label of labels) addRepresentative(target, key, label)
  }
}

function consumerScoreSignature(chart) {
  const palaces = chart.palaces.map((palace) => {
    const scoredStars = [...palace.majorStars, ...palace.minorStars, ...palace.adjectiveStars]
      .filter((star) => MAJOR[star.name] || AUSPICIOUS.has(star.name) || CHALLENGING.has(star.name) || MUTAGEN[star.mutagen])
      .map((star) => `${star.name}:${star.brightness ?? ""}:${star.mutagen ?? ""}`)
      .sort()
      .join(",")
    return `${palace.index}:${palace.name}:${palace.isBodyPalace ? 1 : 0}:${scoredStars}`
  }).join("|")
  return `${chart.soul ?? ""}:${chart.body ?? ""}|${palaces}`
}

function lifeComboLabel(cohortId) {
  const combo = cohortId.replace(/^life_combo\./, "")
  if (!combo || combo === "empty") return "空宫借星"
  return combo.split("-").map((slug) => MAJOR_LABEL_BY_SLUG[slug] ?? slug).join("×")
}

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

async function runSlice(startDay, endDay) {
  const counts = new Map()
  const scoreHistograms = emptyScoreHistograms()
  const cohortHistograms = {}
  const cohortWeights = {}
  const archetypeWeights = {}
  const structuralFamilyWeights = {}
  const archetypeDefinitions = {}
  const archetypeRepresentatives = {}
  const structuralFamilyRepresentatives = {}
  const scoreChart = await consumerScorer()
  const scoreCache = new Map()
  let sampleWeight = 0
  let uniqueStateCount = 0
  for (let day = startDay; day < endDay; day += 1) {
    const cursor = new Date(START.getTime() + day * 86400000)
    const date = `${cursor.getUTCFullYear()}-${cursor.getUTCMonth() + 1}-${cursor.getUTCDate()}`
    for (const [timeIndex, hourWeight] of TIME_INDEX_WEIGHTS.entries()) {
      // Only invariant natal structure is measured. Gender-dependent period
      // direction and labels are outside this feature registry.
      const chart = astro().withOptions({
        type: "solar",
        dateStr: date,
        timeIndex,
        gender: "男",
        isLeapMonth: false,
        fixLeap: true,
        language: "zh-CN",
        config: {
          algorithm: "default",
          dayDivide: "forward",
          yearDivide: "exact",
          horoscopeDivide: "exact",
        },
        astroType: "heaven",
      })
      for (const featureId of features(chart)) counts.set(featureId, (counts.get(featureId) ?? 0) + hourWeight)
      const scoreSignature = consumerScoreSignature(chart)
      let consumer = scoreCache.get(scoreSignature)
      if (!consumer) {
        consumer = scoreChart(chart)
        scoreCache.set(scoreSignature, consumer)
      }
      for (const featureId of consumer.achievement_feature_ids) counts.set(featureId, (counts.get(featureId) ?? 0) + hourWeight)
      const cohortId = consumer.cohort_id
      const archetypeId = consumer.archetype.id
      const structuralFamilyId = `${cohortId}|${archetypeId}`
      const representative = `${date.replaceAll("-", ".")} · ${TIME_INDEX_LABELS[timeIndex]}时段`
      cohortHistograms[cohortId] ??= emptyScoreHistograms()
      cohortWeights[cohortId] = (cohortWeights[cohortId] ?? 0) + hourWeight
      archetypeWeights[archetypeId] = (archetypeWeights[archetypeId] ?? 0) + hourWeight
      structuralFamilyWeights[structuralFamilyId] = (structuralFamilyWeights[structuralFamilyId] ?? 0) + hourWeight
      archetypeDefinitions[archetypeId] = consumer.archetype
      addRepresentative(archetypeRepresentatives, archetypeId, representative)
      addRepresentative(structuralFamilyRepresentatives, structuralFamilyId, representative)
      counts.set(`ziwei.archetype.${archetypeId}`, (counts.get(`ziwei.archetype.${archetypeId}`) ?? 0) + hourWeight)
      for (const key of SCORE_KEYS) {
        addHistogramValue(scoreHistograms[key], consumer.scores[key], hourWeight)
        addHistogramValue(cohortHistograms[cohortId][key], consumer.scores[key], hourWeight)
      }
      sampleWeight += hourWeight
      uniqueStateCount += 1
    }
  }
  return { counts: Object.fromEntries(counts), scoreHistograms, cohortHistograms, cohortWeights, archetypeWeights, structuralFamilyWeights, archetypeDefinitions, archetypeRepresentatives, structuralFamilyRepresentatives, sampleWeight, uniqueStateCount }
}

function buildPayload(counts, scoreHistograms, cohortHistograms, cohortWeights, archetypeWeights, structuralFamilyWeights, archetypeDefinitions, archetypeRepresentatives, structuralFamilyRepresentatives, sampleWeight, uniqueStateCount) {
  const supported = supportedFeatureCatalog()
  for (const featureId of Object.keys(counts)) supported.add(featureId)
  const featureCatalog = [...supported].sort((left, right) => left.localeCompare(right))
  const archetypeFamilies = Object.entries(archetypeWeights).map(([archetypeId, weight]) => {
    const definition = archetypeDefinitions[archetypeId]
    return {
      id: `archetype.${archetypeId}`,
      title: `${definition?.title ?? archetypeId}结构族`,
      title_en: `${definition?.title_en ?? archetypeId} family`,
      summary: definition?.summary ?? "同一主导星曜结构的人，共享相近的决策与行动节奏。",
      summary_en: definition?.summary_en ?? "Charts in this family share a similar decision and action rhythm.",
      features: [`archetype:${archetypeId}`],
      archetype_id: archetypeId,
      weight,
      total_weight: sampleWeight,
      share_percentage: Number((weight / sampleWeight * 100).toFixed(6)),
      representatives: archetypeRepresentatives[archetypeId] ?? [],
    }
  })
  const jointFamilies = Object.entries(structuralFamilyWeights).map(([familyId, weight]) => {
    const [cohortId, archetypeId] = familyId.split("|")
    const definition = archetypeDefinitions[archetypeId]
    const lifeLabel = lifeComboLabel(cohortId)
    return {
      id: `joint.${cohortId}.${archetypeId}`,
      title: `${lifeLabel} · ${definition?.title ?? archetypeId}`,
      title_en: `${lifeLabel} · ${definition?.title_en ?? archetypeId}`,
      summary: `命宫以${lifeLabel}为主轴，并呈现“${definition?.title ?? archetypeId}”的行动节奏。`,
      summary_en: `This life-star axis expresses the ${definition?.title_en ?? archetypeId} rhythm.`,
      features: [`life:${cohortId.replace(/^life_combo\./, "")}`, `archetype:${archetypeId}`],
      archetype_id: archetypeId,
      weight,
      total_weight: sampleWeight,
      share_percentage: Number((weight / sampleWeight * 100).toFixed(6)),
      representatives: structuralFamilyRepresentatives[familyId] ?? [],
    }
  })
  const consumerBaseline = {
    schema_version: 1,
    id: `${BASELINE_ID}-${CONSUMER_RULES_VERSION}`,
    rules_version: CONSUMER_RULES_VERSION,
    score_keys: SCORE_KEYS,
    sample_weight: sampleWeight,
    weighted_unit: "civil_hour",
    histograms: scoreHistograms,
    cohort_key: "life_palace_major_star_combination",
    cohort_weights: Object.fromEntries(Object.entries(cohortWeights).sort(([left], [right]) => left.localeCompare(right))),
    cohort_histograms: Object.fromEntries(Object.entries(cohortHistograms).sort(([left], [right]) => left.localeCompare(right))),
    structural_families: [...jointFamilies, ...archetypeFamilies].sort((left, right) => right.weight - left.weight || left.id.localeCompare(right.id)),
    method: "Weighted empirical score histograms from the same versioned natal scoring function; compact aggregates only, no chart samples retained.",
  }
  consumerBaseline.hash = sha256Value(consumerBaseline)
  return {
    schema_version: SCHEMA_VERSION,
    id: BASELINE_ID,
    chart_type: "ziwei",
    kind: "calendar_sample_frequency",
    label: "1924-02-05—2044-02-04（不含）紫微标准历法样本",
    start: "1924-02-05",
    end: "2044-02-04",
    interval_semantics: "[start, end) civil dates",
    timezone: "Asia/Shanghai",
    day_boundary: "forward",
    config_id: CONFIG_ID,
    config: {
      calendar: "solar",
      algorithm: "default",
      day_boundary: "forward",
      year_boundary: "exact",
      fix_leap: true,
      astro_type: "heaven",
    },
    engine: "iztro 2.5.8",
    rules_version: RULES_VERSION,
    rules_registry_hash: sha256Value(REGISTRY_DESCRIPTOR),
    feature_catalog: featureCatalog,
    feature_catalog_hash: sha256Value(featureCatalog),
    unique_state_count: uniqueStateCount,
    sample_unit: "calendar_state",
    weighted_unit: "civil_hour",
    sample_weight: sampleWeight,
    time_index_weights: TIME_INDEX_WEIGHTS,
    method: "逐日 × 13 个民用时段索引穷举，早子/晚子各按 1 小时、其余索引各按 2 小时加权；仅计算男性本命结构，登记特征不含随性别变化的运限方向与标签。",
    gender_scope: "male_only_natal_structure_gender_invariant",
    features: Object.fromEntries(featureCatalog.map((featureId) => [featureId, { hit_weight: counts[featureId] ?? 0 }])),
    consumer_baseline: consumerBaseline,
  }
}

function stableStringify(value) {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`
  return JSON.stringify(value)
}

function sha256Value(value) {
  return `sha256:${crypto.createHash("sha256").update(stableStringify(value)).digest("hex")}`
}

function generatorMetadata() {
  const totalDays = Math.round((END.getTime() - START.getTime()) / 86400000)
  return {
    schema_version: SCHEMA_VERSION,
    config_id: CONFIG_ID,
    time_index_weights: TIME_INDEX_WEIGHTS,
    gender_scope: "male_only_natal_structure_gender_invariant",
    unique_state_count: totalDays * TIME_INDEX_WEIGHTS.length,
    sample_weight: totalDays * TIME_INDEX_WEIGHTS.reduce((total, weight) => total + weight, 0),
    weighted_unit: "civil_hour",
    rules_registry_hash: sha256Value(REGISTRY_DESCRIPTOR),
    consumer_rules_version: CONSUMER_RULES_VERSION,
    consumer_score_keys: SCORE_KEYS,
  }
}

if (isMainThread && process.argv.includes("--metadata")) {
  process.stdout.write(`${JSON.stringify(generatorMetadata())}\n`)
} else if (!isMainThread) {
  parentPort.postMessage(await runSlice(workerData.startDay, workerData.endDay))
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
  const scoreHistograms = emptyScoreHistograms()
  const cohortHistograms = {}
  const cohortWeights = {}
  const archetypeWeights = {}
  const structuralFamilyWeights = {}
  const archetypeDefinitions = {}
  const archetypeRepresentatives = {}
  const structuralFamilyRepresentatives = {}
  let sampleWeight = 0
  let uniqueStateCount = 0
  for (const result of results) {
    sampleWeight += result.sampleWeight
    uniqueStateCount += result.uniqueStateCount
    for (const [featureId, hitWeight] of Object.entries(result.counts)) counts[featureId] = (counts[featureId] ?? 0) + hitWeight
    mergeScoreHistograms(scoreHistograms, result.scoreHistograms)
    for (const [cohortId, histograms] of Object.entries(result.cohortHistograms)) {
      cohortHistograms[cohortId] ??= emptyScoreHistograms()
      mergeScoreHistograms(cohortHistograms[cohortId], histograms)
    }
    for (const [cohortId, weight] of Object.entries(result.cohortWeights)) cohortWeights[cohortId] = (cohortWeights[cohortId] ?? 0) + weight
    for (const [archetypeId, weight] of Object.entries(result.archetypeWeights)) archetypeWeights[archetypeId] = (archetypeWeights[archetypeId] ?? 0) + weight
    for (const [familyId, weight] of Object.entries(result.structuralFamilyWeights)) structuralFamilyWeights[familyId] = (structuralFamilyWeights[familyId] ?? 0) + weight
    Object.assign(archetypeDefinitions, result.archetypeDefinitions)
    mergeRepresentatives(archetypeRepresentatives, result.archetypeRepresentatives)
    mergeRepresentatives(structuralFamilyRepresentatives, result.structuralFamilyRepresentatives)
  }
  const payload = buildPayload(counts, scoreHistograms, cohortHistograms, cohortWeights, archetypeWeights, structuralFamilyWeights, archetypeDefinitions, archetypeRepresentatives, structuralFamilyRepresentatives, sampleWeight, uniqueStateCount)
  payload.hash = sha256Value(payload)
  fs.mkdirSync(path.dirname(OUTPUT), { recursive: true })
  fs.writeFileSync(OUTPUT, `${JSON.stringify(payload, null, 2)}\n`)
  process.stdout.write(`${OUTPUT}: ${uniqueStateCount} unique states, ${sampleWeight} civil-hour weight, ${payload.hash}\n`)
}
