import fs from "node:fs"
import path from "node:path"
import vm from "node:vm"
import crypto from "node:crypto"
import { createRequire } from "node:module"
import { fileURLToPath } from "node:url"
import { Worker, isMainThread, parentPort, workerData } from "node:worker_threads"
import os from "node:os"
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const require = createRequire(import.meta.url)
const { astro } = require(path.join(root, "frontend/node_modules/iztro"))
const ts = require(path.join(root, "frontend/node_modules/typescript"))
const cache = new Map()
function load(name) {
  if (cache.has(name)) return cache.get(name)
  const source = fs.readFileSync(path.join(root, `frontend/src/lib/${name}.ts`), "utf8")
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText
  const module = { exports: {} }; cache.set(name, module.exports)
  vm.runInThisContext(`(function(require,module,exports){${code}\n})`)((id) => id.startsWith("@/lib/") ? load(id.slice(6)) : require(id), module, module.exports)
  return module.exports
}
const featureModule = load("ziwei-statistics")
const START = Date.UTC(1950, 0, 1), END = Date.UTC(2030, 0, 1)
const DAYS = (END - START) / 86400000
const WEIGHTS = [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1]
const CONFIG_ID = "ziwei-standard-v1"
const DESCRIPTOR = { rules_version: featureModule.ZIWEI_LIFE_RULES_VERSION, encoding_version: 2, feature_families: ["life_combo", "life_state", "life_count", "life_star"], scope: "fourteen_major_stars_in_life_palace_only", brightness: ["miao", "wang", "de", "li", "ping", "bu", "xian", "unknown"] }
const stable = (v) => Array.isArray(v) ? v.map(stable) : v && typeof v === "object" ? Object.fromEntries(Object.keys(v).sort().map((key) => [key, stable(v[key])])) : v
const hash = (v) => `sha256:${crypto.createHash("sha256").update(JSON.stringify(stable(v))).digest("hex")}`
function calculate(start, end) {
  const counts = {}, multiplicities = {}
  for (let day = start; day < end; day++) {
    const date = new Date(START + day * 86400000).toISOString().slice(0, 10)
    for (let timeIndex = 0; timeIndex < 13; timeIndex++) {
      const chart = astro.withOptions({ type: "solar", dateStr: date, timeIndex, gender: "男", isLeapMonth: false, fixLeap: true, language: "zh-CN", config: { algorithm: "default", dayDivide: "forward", yearDivide: "exact", horoscopeDivide: "exact" }, astroType: "heaven" })
      const size = featureModule.ziweiLifeStars(chart).length
      multiplicities[size] = (multiplicities[size] ?? 0) + WEIGHTS[timeIndex]
      for (const id of featureModule.ziweiFeatureIds(chart)) counts[id] = (counts[id] ?? 0) + WEIGHTS[timeIndex]
    }
  }
  return { counts, multiplicities }
}
if (!isMainThread) parentPort.postMessage(calculate(workerData.start, workerData.end))
else if (process.argv.includes("--metadata")) {
  console.log(JSON.stringify({ schema_version: 4, config_id: CONFIG_ID, time_index_weights: WEIGHTS, gender_scope: "male_only_natal_structure_gender_invariant", unique_state_count: DAYS * 13, sample_weight: DAYS * 24, weighted_unit: "civil_hour", rules_registry_hash: hash(DESCRIPTOR) }))
}
else {
  const workers = Math.min(4, os.availableParallelism())
  const results = await Promise.all(Array.from({ length: workers }, (_, i) => new Promise((resolve, reject) => {
    const worker = new Worker(new URL(import.meta.url), { workerData: { start: Math.floor(DAYS * i / workers), end: Math.floor(DAYS * (i + 1) / workers) } })
    worker.once("message", resolve); worker.once("error", reject); worker.once("exit", (code) => { if (code) reject(new Error(`worker exited ${code}`)) })
  })))
  const counts = {}, multiplicities = {}
  for (const result of results) {
    for (const [key, value] of Object.entries(result.counts)) counts[key] = (counts[key] ?? 0) + value
    for (const [key, value] of Object.entries(result.multiplicities)) multiplicities[key] = (multiplicities[key] ?? 0) + value
  }
  for (const id of Object.values(featureModule.MAJOR_STAR_IDS)) for (const brightness of ["present", ...DESCRIPTOR.brightness]) counts[`ziwei.life_star.${id}.${brightness}`] ??= 0
  for (const count of [0, 1, 2]) counts[`ziwei.life_count.${count}`] ??= 0
  const catalog = Object.keys(counts).sort()
  const total = DAYS * 24
  for (const prefix of ["ziwei.life_combo.", "ziwei.life_state.", "ziwei.life_count."]) {
    const sum = catalog.filter((key) => key.startsWith(prefix)).reduce((sum, key) => sum + counts[key], 0)
    if (sum !== total) throw new Error(`Partition denominator mismatch: ${prefix}`)
  }
  const payload = {
    schema_version: 4, id: featureModule.ZIWEI_BASELINE_ID, chart_type: "ziwei", kind: "calendar_sample_frequency",
    label: "1950—2029 年命宫主星历法参考（80 年）", start: "1950-01-01", end: "2030-01-01", interval_semantics: "[start, end) civil dates",
    timezone: "Asia/Shanghai", day_boundary: "forward", config_id: CONFIG_ID,
    config: { calendar: "solar", algorithm: "default", day_boundary: "forward", year_boundary: "exact", fix_leap: true, astro_type: "heaven" },
    engine: "iztro 2.5.8", rules_version: featureModule.ZIWEI_LIFE_RULES_VERSION, rules_registry_hash: hash(DESCRIPTOR),
    feature_catalog: catalog, feature_catalog_hash: hash(catalog), unique_state_count: DAYS * 13,
    sample_unit: "date_time_index", weighted_unit: "civil_hour", sample_weight: total, time_index_weights: WEIGHTS,
    method: "逐日 × 13 时段索引；早子、晚子各 1 小时，其余各 2 小时。只统计命宫十四主星无序组合及逐星亮度，未知亮度单列。非人口出生分布。",
    gender_scope: "male_only_natal_structure_gender_invariant", life_star_count_weights: multiplicities,
    features: Object.fromEntries(catalog.map((key) => [key, { hit_weight: counts[key] }])),
  }
  payload.hash = hash(payload)
  const target = path.join(root, `src/iching/core/data/${payload.id}.json`)
  fs.writeFileSync(`${target}.tmp`, JSON.stringify(payload) + "\n"); fs.renameSync(`${target}.tmp`, target)
  console.log(`${target}: ${total} weighted hours; major-star counts ${JSON.stringify(multiplicities)}`)
}
