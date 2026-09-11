import assert from "node:assert/strict"
import test from "node:test"
import { buildZiweiConsumerProfile, lifeFeaturePercentage } from "../src/lib/ziwei-consumer.ts"
import { ZIWEI_BASELINE_ID, ziweiFeatureIds, ziweiLifeStars } from "../src/lib/ziwei-statistics.ts"
const chart = { palaces: [
  { name: "命宫", majorStars: [{ name: "武曲", brightness: "旺" }, { name: "天府", brightness: "庙" }] },
  { name: "迁移", majorStars: [{ name: "紫微", brightness: "陷" }] },
] }
test("life-palace events match each named star and brightness exactly", () => {
  const features = ziweiFeatureIds(chart)
  assert.ok(features.includes("ziwei.life_combo.tianfu-wuqu"))
  assert.ok(features.includes("ziwei.life_state.tianfu_miao-wuqu_wang"))
  assert.ok(!features.some((id) => id.includes(".ziwei.")))
  assert.equal(ziweiLifeStars({ palaces: [{ name: "命宫", majorStars: [{ name: "紫微" }] }] })[0].brightness, "unknown")
})
test("absent, stale and unsupported statistics cannot invent a percentage", () => {
  const id = "ziwei.life_combo.tianfu-wuqu"
  assert.equal(lifeFeaturePercentage(undefined, id), null)
  const stats = { status: "available", baseline: { id: ZIWEI_BASELINE_ID }, rarity_metrics: [{ feature_id: id, status: "observed", percentage: 1.23456 }] }
  assert.equal(lifeFeaturePercentage(stats, id), 1.23456)
  assert.equal(lifeFeaturePercentage(stats, "ziwei.life_combo.other"), null)
  assert.equal(lifeFeaturePercentage({ ...stats, baseline: { id: "old" } }, id), null)
  const profile = buildZiweiConsumerProfile(chart, null)
  assert.ok(profile.fingerprints.every((item) => item.incidence_percentage === null))
  assert.deepEqual(profile.achievements, [])
  assert.deepEqual(profile.subjects, [])
  assert.equal(profile.twin, null)
})
