import assert from "node:assert/strict"
import test from "node:test"

import { buildZiweiConsumerProfile, rebaseZiweiPeriodActivity } from "../src/lib/ziwei-consumer.ts"

const keys = ["overall", "career", "wealth", "relationship", "health"]

test("period activity cancels every natal heuristic at the personal midpoint", () => {
  for (const natal of [
    { overall: 18, career: 22, wealth: 31, relationship: 44, health: 57 },
    { overall: 92, career: 88, wealth: 79, relationship: 66, health: 53 },
  ]) {
    assert.deepEqual(rebaseZiweiPeriodActivity(natal, { ...natal }), Object.fromEntries(keys.map((key) => [key, 50])))
  }
})

test("new Ziwei profiles expose paths rather than life-quality scores", () => {
  const names = ["命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "交友", "官禄", "田宅", "福德", "父母"]
  const branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
  const chart = {
    palaces: names.map((name, index) => ({
      index,
      name,
      heavenlyStem: "甲",
      earthlyBranch: branches[index],
      isBodyPalace: index === 0,
      majorStars: index === 0 ? [{ name: "紫微", brightness: "庙", mutagen: "禄" }] : [],
      minorStars: [],
      adjectiveStars: [],
    })),
  }
  const profile = buildZiweiConsumerProfile(chart, null)

  for (const key of ["main_score", "global_percentile", "global_top_percentage", "cohort_percentile", "cohort_top_percentage"]) {
    assert.equal(key in profile.identity, false)
  }
  for (const subject of profile.subjects) {
    for (const key of ["score", "global_percentile", "global_top_percentage", "cohort_percentile", "cohort_top_percentage"]) {
      assert.equal(key in subject, false)
    }
    assert.ok(subject.path_label)
    assert.ok(subject.path_summary)
  }
  assert.equal("raw_scores" in profile.metadata, false)
  assert.equal("rank_sources" in profile.metadata, false)
})
