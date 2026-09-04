export type ZiweiLocale = "en" | "zh"

type Term = {
  zh: string
  pinyin: string
  aliases: readonly string[]
}

const STAR_TERMS: readonly Term[] = [
  { zh: "紫微", pinyin: "Zǐ Wēi", aliases: ["emperor"] },
  { zh: "天机", pinyin: "Tiān Jī", aliases: ["天機", "advisor"] },
  { zh: "太阳", pinyin: "Tài Yáng", aliases: ["太陽", "sun"] },
  { zh: "武曲", pinyin: "Wǔ Qǔ", aliases: ["general"] },
  { zh: "天同", pinyin: "Tiān Tóng", aliases: ["fortunate"] },
  { zh: "廉贞", pinyin: "Lián Zhēn", aliases: ["廉貞", "judge"] },
  { zh: "天府", pinyin: "Tiān Fǔ", aliases: ["empress"] },
  { zh: "太阴", pinyin: "Tài Yīn", aliases: ["太陰", "moon"] },
  { zh: "贪狼", pinyin: "Tān Láng", aliases: ["貪狼", "wolf"] },
  { zh: "巨门", pinyin: "Jù Mén", aliases: ["巨門", "advocator"] },
  { zh: "天相", pinyin: "Tiān Xiàng", aliases: ["minister"] },
  { zh: "天梁", pinyin: "Tiān Liáng", aliases: ["sage"] },
  { zh: "七杀", pinyin: "Qī Shā", aliases: ["七殺", "marshal"] },
  { zh: "破军", pinyin: "Pò Jūn", aliases: ["破軍", "rebel"] },
  { zh: "左辅", pinyin: "Zuǒ Fǔ", aliases: ["左輔", "officer"] },
  { zh: "右弼", pinyin: "Yòu Bì", aliases: ["helper"] },
  { zh: "文昌", pinyin: "Wén Chāng", aliases: ["scholar"] },
  { zh: "文曲", pinyin: "Wén Qǔ", aliases: ["artist"] },
  { zh: "天魁", pinyin: "Tiān Kuí", aliases: ["assistant"] },
  { zh: "天钺", pinyin: "Tiān Yuè", aliases: ["天鉞", "aide"] },
  { zh: "擎羊", pinyin: "Qíng Yáng", aliases: ["driven"] },
  { zh: "陀罗", pinyin: "Tuó Luó", aliases: ["陀羅", "tangled"] },
  { zh: "火星", pinyin: "Huǒ Xīng", aliases: ["impulsive"] },
  { zh: "铃星", pinyin: "Líng Xīng", aliases: ["鈴星", "spark"] },
  { zh: "地空", pinyin: "Dì Kōng", aliases: ["ideologue"] },
  { zh: "地劫", pinyin: "Dì Jié", aliases: ["fickle"] },
]

const PALACE_TERMS: readonly Term[] = [
  { zh: "命宫", pinyin: "Mìng Gōng", aliases: ["命宮", "soul", "life"] },
  { zh: "兄弟宫", pinyin: "Xiōng Dì Gōng", aliases: ["兄弟", "siblings"] },
  { zh: "夫妻宫", pinyin: "Fū Qī Gōng", aliases: ["夫妻", "spouse", "relationship"] },
  { zh: "子女宫", pinyin: "Zǐ Nǚ Gōng", aliases: ["子女", "children"] },
  { zh: "财帛宫", pinyin: "Cái Bó Gōng", aliases: ["財帛宮", "财帛", "財帛", "wealth"] },
  { zh: "疾厄宫", pinyin: "Jí È Gōng", aliases: ["疾厄", "health"] },
  { zh: "迁移宫", pinyin: "Qiān Yí Gōng", aliases: ["遷移宮", "迁移", "遷移", "surface", "travel"] },
  { zh: "交友宫", pinyin: "Jiāo Yǒu Gōng", aliases: ["交友", "仆役", "僕役", "friends"] },
  { zh: "官禄宫", pinyin: "Guān Lù Gōng", aliases: ["官祿宮", "官禄", "官祿", "career"] },
  { zh: "田宅宫", pinyin: "Tián Zhái Gōng", aliases: ["田宅", "property"] },
  { zh: "福德宫", pinyin: "Fú Dé Gōng", aliases: ["福德", "spirit"] },
  { zh: "父母宫", pinyin: "Fù Mǔ Gōng", aliases: ["父母", "parents"] },
]

const TRANSFORMATION_TERMS: readonly Term[] = [
  { zh: "化禄", pinyin: "Huà Lù", aliases: ["禄", "祿", "prosperity", "a"] },
  { zh: "化权", pinyin: "Huà Quán", aliases: ["权", "權", "power", "b"] },
  { zh: "化科", pinyin: "Huà Kē", aliases: ["科", "merit", "c"] },
  { zh: "化忌", pinyin: "Huà Jì", aliases: ["忌", "obstacle", "d"] },
]

function normalize(value: string) {
  return value.trim().toLowerCase()
}

function findTerm(terms: readonly Term[], value: string) {
  const key = normalize(value)
  return terms.find((term) => normalize(term.zh) === key || term.aliases.some((alias) => normalize(alias) === key))
}

function render(term: Term | undefined, fallback: string, locale: ZiweiLocale) {
  if (!term) return fallback
  return locale === "zh" ? term.zh : `${term.zh} · ${term.pinyin}`
}

export function canonicalZiweiStarName(value: string, locale: ZiweiLocale) {
  return render(findTerm(STAR_TERMS, value), value, locale)
}

export function canonicalZiweiPalaceName(value: string, locale: ZiweiLocale) {
  return render(findTerm(PALACE_TERMS, value), value, locale)
}

export function canonicalZiweiTransformationName(value: string, locale: ZiweiLocale) {
  const bareValue = value.replace(/^化/, "")
  return render(
    findTerm(TRANSFORMATION_TERMS, value) ?? findTerm(TRANSFORMATION_TERMS, bareValue),
    value,
    locale,
  )
}
