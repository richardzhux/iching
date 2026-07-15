import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"
import type { IFunctionalHoroscope } from "iztro/lib/astro/FunctionalHoroscope"
import type { IFunctionalPalace } from "iztro/lib/astro/FunctionalPalace"
import type { HoroscopeItem } from "iztro/lib/data/types"

export const ZIWEI_CONSUMER_RULES_VERSION = "ziwei-consumer-c1"

export type ZiweiScoreKey = "overall" | "career" | "wealth" | "relationship" | "health"
type ZiweiThemeKey = Exclude<ZiweiScoreKey, "overall">
type ConsumerLocale = "zh" | "en"
type RankSource = "empirical_baseline" | "deterministic_fallback"

export type ZiweiHistogramBin = {
  value: number
  weight: number
}

export type ZiweiScoreDistribution =
  | readonly number[]
  | { bins: readonly ZiweiHistogramBin[] }
  | { histogram: readonly ZiweiHistogramBin[] }
  | { values: readonly number[]; weights?: readonly number[] }
  | Record<string, number>

export type ZiweiStructuralFamilyBaseline = {
  id: string
  title: string
  title_en?: string
  summary: string
  summary_en?: string
  features: string[]
  archetype_id?: string
  share_percentage?: number
  weight?: number
  total_weight?: number
  representatives?: Array<string | { label?: string; state?: string; date?: string }>
}

export type ZiweiConsumerBaseline = {
  id: string
  histograms: Partial<Record<ZiweiScoreKey, ZiweiScoreDistribution>>
  cohort_histograms: Record<string, Partial<Record<ZiweiScoreKey, ZiweiScoreDistribution>>>
  structural_families: ZiweiStructuralFamilyBaseline[]
  hash?: string
  method?: string
}

export type ZiweiRankResult = {
  raw_score: number
  score: number
  percentile: number
  top_percentage: number
  global_percentile: number
  global_top_percentage: number
  source: RankSource
  sample_weight: number | null
}

export type ZiweiConsumerIdentity = {
  system_title: string
  archetype_title: string
  archetype_subtitle: string
  fusion_title?: string
  main_score: number
  global_percentile: number
  global_top_percentage: number
  cohort_percentile: number
  cohort_top_percentage: number
  cohort_label: string
}

export type ZiweiConsumerSubject = {
  key: ZiweiThemeKey
  label: string
  score: number
  global_percentile: number
  global_top_percentage: number
  cohort_percentile: number
  cohort_top_percentage: number
  headline: string
}

export type ZiweiConsumerFingerprint = {
  id: string
  title: string
  detail: string
  rarity_label: string
  top_percentage: number
}

export type ZiweiConsumerAchievement = {
  id: string
  title: string
  tier: "SSR" | "SR" | "R"
  state: "发力" | "有力" | "可见" | "受制"
  rarity_percentage: number
  position: string
  summary: string
  member_ids: string[]
}

export type ZiweiStructuralTwin = {
  family_id: string
  title: string
  share_percentage: number
  summary: string
  representatives: string[]
}

export type ZiweiKlineMonth = {
  index: number
  label: string
  ganzhi: string
  value: number
  delta: number
  drivers: string[]
}

export type ZiweiKlinePoint = {
  year: number
  open: number
  close: number
  high: number
  low: number
  volume: number
  ma3: number | null
  ma5: number | null
  ma10: number | null
  months: ZiweiKlineMonth[]
}

export type ZiweiKlineSeries = {
  key: ZiweiScoreKey
  label: string
  color: string
  points: ZiweiKlinePoint[]
}

export type ZiweiKlineStage = {
  key: ZiweiScoreKey
  label: string
  year: number
  score: number
  theme: string
  summary: string
}

export type ZiweiKlinePeriodBand = {
  label: string
  start_year: number
  end_year: number
}

export type ZiweiLifeKline = {
  default_window: {
    start_year: number
    end_year: number
  }
  series: ZiweiKlineSeries[]
  period_bands: ZiweiKlinePeriodBand[]
  stages: ZiweiKlineStage[]
  method: "iztro_monthly_midpoint_annual_ohlcv"
}

export type ZiweiConsumerProfile = {
  version: typeof ZIWEI_CONSUMER_RULES_VERSION
  system: "ziwei"
  identity: ZiweiConsumerIdentity
  subjects: ZiweiConsumerSubject[]
  achievements: ZiweiConsumerAchievement[]
  fingerprints: ZiweiConsumerFingerprint[]
  twin: ZiweiStructuralTwin
  life_kline: ZiweiLifeKline
  capability_key: null
  metadata: {
    rules_version: typeof ZIWEI_CONSUMER_RULES_VERSION
    archetype_id: ZiweiArchetypeId
    cohort_id: string
    baseline_id: string | null
    baseline_hash: string | null
    rank_sources: {
      global: RankSource
      cohort: RankSource
    }
    raw_scores: Record<ZiweiScoreKey, number>
    selected_period: string | null
    scoring_inputs: string[]
    methods: {
      score: string
      rank: string
      kline: string
    }
    sources: string[]
  }
}

type MajorStarId = "ziwei" | "tianji" | "taiyang" | "wuqu" | "tiantong" | "lianzhen" | "tianfu" | "taiyin" | "tanlang" | "jumen" | "tianxiang" | "tianliang" | "qisha" | "pojun"
type StructuralArchetypeId = "stellar-duet" | "borrowed-axis" | "six-aids-network" | "dual-track"
export type ZiweiArchetypeId = MajorStarId | StructuralArchetypeId
type ZiweiFusionFamily = "command" | "strategy" | "resource" | "relation" | "guardian" | "disruption"
type BaziFusionFamily = "authority" | "resource" | "wealth" | "output" | "peer" | "adaptive"

export type ZiweiArchetype = {
  id: ZiweiArchetypeId
  title: string
  title_en: string
  headline: string
  headline_en: string
  family: ZiweiFusionFamily
  anchor_star?: MajorStarId
}

export const ZIWEI_ARCHETYPES: readonly ZiweiArchetype[] = [
  { id: "ziwei", title: "帝星总控者", title_en: "Imperial Orchestrator", headline: "你不是在等位置，你会把全局重新排成自己的位置。", headline_en: "You do not wait for position; you reorganize the field around one.", family: "command", anchor_star: "ziwei" },
  { id: "tianji", title: "变局策士", title_en: "Adaptive Strategist", headline: "别人看见变化，你先看见变化背后的下一步。", headline_en: "Others notice change; you notice the move after it.", family: "strategy", anchor_star: "tianji" },
  { id: "taiyang", title: "场域点灯者", title_en: "Field Illuminator", headline: "你的优势不是低调正确，而是让方向被所有人看见。", headline_en: "Your edge is making the right direction visible to everyone.", family: "command", anchor_star: "taiyang" },
  { id: "wuqu", title: "硬核兑现官", title_en: "Hard-Edge Executor", headline: "你相信能落地的力量，结果就是你的语言。", headline_en: "You trust what can be delivered; results are your language.", family: "resource", anchor_star: "wuqu" },
  { id: "tiantong", title: "柔性复原者", title_en: "Gentle Restorer", headline: "你不靠硬碰硬取胜，你让系统重新有余地。", headline_en: "You win by giving the system room to recover.", family: "relation", anchor_star: "tiantong" },
  { id: "lianzhen", title: "边界重写者", title_en: "Boundary Rewriter", headline: "你最强的时刻，是把模糊规则改成清晰边界。", headline_en: "You are strongest when blurred rules become clear boundaries.", family: "disruption", anchor_star: "lianzhen" },
  { id: "tianfu", title: "资源定盘者", title_en: "Resource Anchor", headline: "你不是囤积资源，你让资源在关键时刻不掉链。", headline_en: "You make resources hold when the stakes rise.", family: "resource", anchor_star: "tianfu" },
  { id: "taiyin", title: "隐线布局者", title_en: "Quiet Architect", headline: "你在安静处完成最深的布局，再让结果自己出现。", headline_en: "You build quietly and let the result announce itself.", family: "strategy", anchor_star: "taiyin" },
  { id: "tanlang", title: "魅力造浪者", title_en: "Magnetic Wave-Maker", headline: "你会把欲望、机会与人群，变成一股向前的浪。", headline_en: "You turn appetite, opportunity, and people into momentum.", family: "relation", anchor_star: "tanlang" },
  { id: "jumen", title: "议题破壁者", title_en: "Narrative Breaker", headline: "你靠说清别人不敢说的事，打开被封住的局面。", headline_en: "You unlock stuck situations by naming what others avoid.", family: "strategy", anchor_star: "jumen" },
  { id: "tianxiang", title: "秩序校准者", title_en: "Order Calibrator", headline: "你不是维持表面和平，你让复杂协作重新对齐。", headline_en: "You realign complex cooperation, not merely preserve calm.", family: "command", anchor_star: "tianxiang" },
  { id: "tianliang", title: "逆风护航者", title_en: "Storm Guardian", headline: "局面越难，你越能成为那个不失原则的支点。", headline_en: "The harder the conditions, the steadier your principles become.", family: "guardian", anchor_star: "tianliang" },
  { id: "qisha", title: "高压先锋", title_en: "Pressure Vanguard", headline: "你不是为了安全而来，你为突破最难的第一道门而来。", headline_en: "You are built to breach the first hard gate, not seek safety.", family: "disruption", anchor_star: "qisha" },
  { id: "pojun", title: "重启拆局者", title_en: "System Rebooter", headline: "当旧结构失效，你敢先拆掉，再建一个能跑的版本。", headline_en: "When the old structure fails, you rebuild one that can move.", family: "disruption", anchor_star: "pojun" },
  { id: "stellar-duet", title: "双星联席者", title_en: "Dual-Star Director", headline: "你的力量来自两套天性同时在线，而不是只押一个答案。", headline_en: "Your power comes from running two native modes at once.", family: "strategy" },
  { id: "borrowed-axis", title: "借势映照者", title_en: "Borrowed-Axis Reader", headline: "你的命宫不抢镜，但你极会借对面与全局完成自己。", headline_en: "Your center stays quiet while the wider field completes the picture.", family: "guardian" },
  { id: "six-aids-network", title: "六曜共振者", title_en: "Six-Aids Constellation", headline: "你真正稀缺的不是单点天赋，而是关键帮助总能连成网。", headline_en: "Your rare advantage is support that repeatedly forms a network.", family: "resource" },
  { id: "dual-track", title: "双轨进化者", title_en: "Dual-Track Evolver", headline: "你内在的主轴与行动的落点不同，因此比别人多一套人生引擎。", headline_en: "Your inner axis and lived action diverge, giving you a second engine.", family: "command" },
]

export const ZIWEI_BAZI_FUSION_TITLE_MATRIX: Record<ZiweiFusionFamily, Record<BaziFusionFamily, string>> = {
  command: { authority: "王座执令者", resource: "帝国筑基者", wealth: "资本总舵手", output: "宣言发动机", peer: "同盟统合者", adaptive: "变局掌舵者" },
  strategy: { authority: "幕后军师长", resource: "知识架构师", wealth: "机会算法家", output: "洞见放大器", peer: "群体读局者", adaptive: "多线程预判者" },
  resource: { authority: "秩序资产官", resource: "深库守成者", wealth: "复利建仓者", output: "价值生产者", peer: "资源结盟者", adaptive: "韧性配置师" },
  relation: { authority: "魅力号令者", resource: "关系滋养者", wealth: "人脉变现者", output: "影响力造浪者", peer: "圈层连接器", adaptive: "情境变色龙" },
  guardian: { authority: "原则守门人", resource: "庇护筑基者", wealth: "风险保全者", output: "经验传承者", peer: "同路护航者", adaptive: "逆风稳定器" },
  disruption: { authority: "铁腕破局者", resource: "废墟重建者", wealth: "高波动猎手", output: "规则爆破者", peer: "前线集结者", adaptive: "极限重启者" },
}

export const ZIWEI_ARCHETYPE_FUSION_TITLE_MATRIX = Object.fromEntries(
  ZIWEI_ARCHETYPES.map((archetype) => [archetype.id, ZIWEI_BAZI_FUSION_TITLE_MATRIX[archetype.family]]),
) as Record<ZiweiArchetypeId, Record<BaziFusionFamily, string>>

const BAZI_FUSION_KEYWORDS: Record<BaziFusionFamily, readonly string[]> = {
  authority: ["commander", "finisher", "官", "杀", "刃", "将", "统帅", "领导", "号令", "执行", "终结", "authority", "leader"],
  resource: ["builder", "scholar", "mentor", "guardian", "印", "学堂", "德", "资源", "研究", "体系", "建造", "引导", "守成", "resource"],
  wealth: ["connector", "operator", "财", "禄", "经营", "兑现", "商业", "资本", "wealth", "capital", "merchant"],
  output: ["breaker", "creator", "visionary", "食神", "伤官", "才华", "表达", "创造", "破局", "策划", "output", "voice"],
  peer: ["independent", "diplomat", "integrator", "magnet", "比肩", "劫财", "同盟", "独立", "协调", "整合", "连接", "魅力", "peer", "alliance", "network"],
  adaptive: ["strategist", "challenger", "catalyst", "从", "专旺", "变", "谋略", "挑战", "催化", "前瞻", "adaptive", "transform", "follow"],
}

export function resolveZiweiBaziFusionTitle(ziweiArchetypeId: ZiweiArchetypeId, baziArchetypeIdOrTitle: string): string {
  const archetype = ZIWEI_ARCHETYPES.find((item) => item.id === ziweiArchetypeId) ?? ZIWEI_ARCHETYPES[0]
  const normalized = baziArchetypeIdOrTitle.toLowerCase()
  const baziFamily = (Object.keys(BAZI_FUSION_KEYWORDS) as BaziFusionFamily[]).find((family) => BAZI_FUSION_KEYWORDS[family].some((keyword) => normalized.includes(keyword.toLowerCase()))) ?? "adaptive"
  return ZIWEI_ARCHETYPE_FUSION_TITLE_MATRIX[archetype.id][baziFamily]
}

type CanonicalPalace = "life" | "siblings" | "spouse" | "children" | "wealth" | "health" | "travel" | "friends" | "career" | "property" | "spirit" | "parents" | "unknown"
type MutagenId = "lu" | "quan" | "ke" | "ji"
type ThemeVector = Record<ZiweiScoreKey, number>

const MAJOR_STAR_ALIASES: Record<string, MajorStarId> = {
  紫微: "ziwei", emperor: "ziwei",
  天机: "tianji", 天機: "tianji", advisor: "tianji",
  太阳: "taiyang", 太陽: "taiyang", sun: "taiyang",
  武曲: "wuqu", general: "wuqu",
  天同: "tiantong", fortunate: "tiantong",
  廉贞: "lianzhen", 廉貞: "lianzhen", judge: "lianzhen",
  天府: "tianfu", empress: "tianfu",
  太阴: "taiyin", 太陰: "taiyin", moon: "taiyin",
  贪狼: "tanlang", 貪狼: "tanlang", wolf: "tanlang",
  巨门: "jumen", 巨門: "jumen", advocator: "jumen",
  天相: "tianxiang", minister: "tianxiang",
  天梁: "tianliang", sage: "tianliang",
  七杀: "qisha", 七殺: "qisha", marshal: "qisha",
  破军: "pojun", 破軍: "pojun", rebel: "pojun",
}

const MAJOR_STAR_LABELS: Record<MajorStarId, { zh: string; en: string }> = {
  ziwei: { zh: "紫微", en: "Emperor" }, tianji: { zh: "天机", en: "Advisor" }, taiyang: { zh: "太阳", en: "Sun" }, wuqu: { zh: "武曲", en: "General" },
  tiantong: { zh: "天同", en: "Fortunate" }, lianzhen: { zh: "廉贞", en: "Judge" }, tianfu: { zh: "天府", en: "Empress" }, taiyin: { zh: "太阴", en: "Moon" },
  tanlang: { zh: "贪狼", en: "Wolf" }, jumen: { zh: "巨门", en: "Advocator" }, tianxiang: { zh: "天相", en: "Minister" }, tianliang: { zh: "天梁", en: "Sage" },
  qisha: { zh: "七杀", en: "Marshal" }, pojun: { zh: "破军", en: "Rebel" },
}

const PALACE_ALIASES: Record<string, CanonicalPalace> = {
  命宫: "life", 命宮: "life", soul: "life", life: "life",
  兄弟: "siblings", siblings: "siblings",
  夫妻: "spouse", spouse: "spouse",
  子女: "children", children: "children",
  财帛: "wealth", 財帛: "wealth", wealth: "wealth",
  疾厄: "health", health: "health",
  迁移: "travel", 遷移: "travel", surface: "travel", travel: "travel",
  仆役: "friends", 僕役: "friends", 交友: "friends", friends: "friends",
  官禄: "career", 官祿: "career", career: "career",
  田宅: "property", property: "property",
  福德: "spirit", spirit: "spirit",
  父母: "parents", parents: "parents",
}

const PALACE_LABELS: Record<CanonicalPalace, { zh: string; en: string }> = {
  life: { zh: "命宫", en: "Life" }, siblings: { zh: "兄弟宫", en: "Siblings" }, spouse: { zh: "夫妻宫", en: "Relationship" }, children: { zh: "子女宫", en: "Children" },
  wealth: { zh: "财帛宫", en: "Wealth" }, health: { zh: "疾厄宫", en: "Health" }, travel: { zh: "迁移宫", en: "Travel" }, friends: { zh: "交友宫", en: "Network" },
  career: { zh: "官禄宫", en: "Career" }, property: { zh: "田宅宫", en: "Property" }, spirit: { zh: "福德宫", en: "Spirit" }, parents: { zh: "父母宫", en: "Parents" },
  unknown: { zh: "未知宫位", en: "Unknown palace" },
}

const AUSPICIOUS_ALIASES: Record<string, string> = {
  左辅: "zuofu", 左輔: "zuofu", officer: "zuofu",
  右弼: "youbi", helper: "youbi",
  文昌: "wenchang", scholar: "wenchang",
  文曲: "wenqu", artist: "wenqu",
  天魁: "tiankui", assistant: "tiankui",
  天钺: "tianyue", 天鉞: "tianyue", aide: "tianyue",
}

const CHALLENGING_ALIASES: Record<string, string> = {
  擎羊: "qingyang", driven: "qingyang",
  陀罗: "tuoluo", 陀羅: "tuoluo", tangled: "tuoluo",
  火星: "huoxing", impulsive: "huoxing",
  铃星: "lingxing", 鈴星: "lingxing", spark: "lingxing",
  地空: "dikong", ideologue: "dikong",
  地劫: "dijie", fickle: "dijie",
}

const AUSPICIOUS_LABELS: Record<string, { zh: string; en: string }> = {
  zuofu: { zh: "左辅", en: "Officer" }, youbi: { zh: "右弼", en: "Helper" }, wenchang: { zh: "文昌", en: "Scholar" }, wenqu: { zh: "文曲", en: "Artist" }, tiankui: { zh: "天魁", en: "Assistant" }, tianyue: { zh: "天钺", en: "Aide" },
}

const CHALLENGING_LABELS: Record<string, { zh: string; en: string }> = {
  qingyang: { zh: "擎羊", en: "Driven" }, tuoluo: { zh: "陀罗", en: "Tangled" }, huoxing: { zh: "火星", en: "Impulsive" }, lingxing: { zh: "铃星", en: "Spark" }, dikong: { zh: "地空", en: "Ideologue" }, dijie: { zh: "地劫", en: "Fickle" },
}

const MUTAGEN_ALIASES: Record<string, MutagenId> = { 禄: "lu", 祿: "lu", A: "lu", 权: "quan", 權: "quan", B: "quan", 科: "ke", C: "ke", 忌: "ji", D: "ji" }
const MUTAGEN_LABELS: Record<MutagenId, { zh: string; en: string }> = {
  lu: { zh: "化禄", en: "Prosperity" }, quan: { zh: "化权", en: "Power" }, ke: { zh: "化科", en: "Merit" }, ji: { zh: "化忌", en: "Obstacle" },
}

const BRIGHTNESS_ADJUSTMENT: Record<string, number> = {
  庙: 0.28, 廟: 0.28, "[+3]": 0.28,
  旺: 0.2, "[+2]": 0.2,
  得: 0.12, "[+1]": 0.12,
  利: 0.05, "[0]": 0.05,
  平: -0.05, "[-1]": -0.05,
  不: -0.14, "[-2]": -0.14,
  陷: -0.26, "[-3]": -0.26,
}

const MAJOR_THEME_VECTORS: Record<MajorStarId, ThemeVector> = {
  ziwei: { overall: 4.8, career: 5.2, wealth: 3.2, relationship: 2.2, health: 2.3 },
  tianji: { overall: 3.6, career: 4.7, wealth: 2.5, relationship: 2.6, health: 2.2 },
  taiyang: { overall: 4.1, career: 5, wealth: 2.4, relationship: 3, health: 2.2 },
  wuqu: { overall: 4, career: 4.6, wealth: 5.2, relationship: 1.2, health: 2.3 },
  tiantong: { overall: 2.7, career: 1.8, wealth: 2.1, relationship: 4.2, health: 4.3 },
  lianzhen: { overall: 3.1, career: 4, wealth: 2.8, relationship: 3.6, health: 1.6 },
  tianfu: { overall: 4.5, career: 3.8, wealth: 5, relationship: 2.7, health: 3.8 },
  taiyin: { overall: 3.6, career: 2.8, wealth: 4.7, relationship: 4, health: 3.1 },
  tanlang: { overall: 3.5, career: 3.4, wealth: 4, relationship: 5.1, health: 1.5 },
  jumen: { overall: 2.8, career: 4.2, wealth: 2.3, relationship: 2.7, health: 1.4 },
  tianxiang: { overall: 4.1, career: 4.8, wealth: 3.1, relationship: 3.8, health: 3 },
  tianliang: { overall: 4.2, career: 3.6, wealth: 1.8, relationship: 3.1, health: 5.2 },
  qisha: { overall: 3.2, career: 5.1, wealth: 3.1, relationship: 0.8, health: 1.4 },
  pojun: { overall: 2.9, career: 4.6, wealth: 3.4, relationship: 1.1, health: 1.1 },
}

const MUTAGEN_THEME_VECTORS: Record<MutagenId, ThemeVector> = {
  lu: { overall: 2.6, career: 1.8, wealth: 4.2, relationship: 1.7, health: 1.1 },
  quan: { overall: 2.4, career: 4.2, wealth: 1.8, relationship: 0.8, health: 0.9 },
  ke: { overall: 2.1, career: 3.1, wealth: 1.1, relationship: 2.4, health: 1.5 },
  ji: { overall: -3.8, career: -3.1, wealth: -3.3, relationship: -3.6, health: -4 },
}

const THEME_PRIMARY_PALACES: Record<ZiweiScoreKey, readonly CanonicalPalace[]> = {
  overall: ["life", "travel"], career: ["career", "life"], wealth: ["wealth", "property"], relationship: ["spouse", "spirit"], health: ["health", "spirit"],
}

const SUBJECT_COPY: Record<ZiweiThemeKey, { label_zh: string; label_en: string; high_zh: string; high_en: string; mid_zh: string; mid_en: string; low_zh: string; low_en: string }> = {
  career: { label_zh: "事业", label_en: "Career", high_zh: "你适合抢主位，不适合长期做隐形齿轮。", high_en: "You are built for the lead seat, not permanent invisibility.", mid_zh: "你靠稳定推进赢，不必每次都抢第一枪。", mid_en: "You win through steady advance, not every first move.", low_zh: "先选对战场，再谈用力；位置比蛮力更重要。", low_en: "Choose the right arena before pushing harder." },
  wealth: { label_zh: "财富", label_en: "Wealth", high_zh: "你有把资源变成杠杆的结构，不只会守成。", high_en: "You can turn resources into leverage, not merely preserve them.", mid_zh: "财富靠节奏和配置增长，不靠一次豪赌。", mid_en: "Wealth grows through pacing and allocation, not one big bet.", low_zh: "先守现金流与边界，再放大收益想象。", low_en: "Protect cash flow and boundaries before chasing upside." },
  relationship: { label_zh: "感情", label_en: "Relationships", high_zh: "你在人际里有强牵引力，也需要同等清晰的边界。", high_en: "You carry strong relational gravity and need equally clear boundaries.", mid_zh: "关系质量取决于说清需求，而不是猜中彼此。", mid_en: "Relationship quality rises when needs are stated, not guessed.", low_zh: "慢一点绑定，先看长期协作是否真的成立。", low_en: "Bind slowly; test whether long-term cooperation is real." },
  health: { label_zh: "健康", label_en: "Health", high_zh: "你的恢复力有底盘，但仍要给高压设置出口。", high_en: "Your recovery base is strong, but pressure still needs an exit.", mid_zh: "稳定作息比偶尔的极限补救更有效。", mid_en: "Consistent rhythm beats occasional heroic recovery.", low_zh: "把恢复当成硬任务，别等身体替你按暂停。", low_en: "Treat recovery as a hard commitment before the body forces a stop." },
}

const SCORE_KEYS: readonly ZiweiScoreKey[] = ["overall", "career", "wealth", "relationship", "health"]
const SUBJECT_KEYS: readonly ZiweiThemeKey[] = ["career", "wealth", "relationship", "health"]
const SCORE_COLORS: Record<ZiweiScoreKey, string> = { overall: "#7c3aed", career: "#2563eb", wealth: "#b7791f", relationship: "#db2777", health: "#059669" }
const FALLBACK_CENTERS: Record<ZiweiScoreKey, number> = { overall: 56, career: 55, wealth: 54, relationship: 53, health: 55 }
const EARTHLY_BRANCH_IDS: Record<string, string> = { 子: "zi", 丑: "chou", 寅: "yin", 卯: "mao", 辰: "chen", 巳: "si", 午: "wu", 未: "wei", 申: "shen", 酉: "you", 戌: "xu", 亥: "hai" }

function clamp(value: number, min = 0, max = 100): number {
  return Math.min(max, Math.max(min, Number.isFinite(value) ? value : min))
}

function round1(value: number): number {
  return Math.round((value + Number.EPSILON) * 10) / 10
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null
}

function asFiniteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

function stableHash(value: string): number {
  let result = 2166136261
  for (let index = 0; index < value.length; index += 1) {
    result ^= value.charCodeAt(index)
    result = Math.imul(result, 16777619)
  }
  return result >>> 0
}

function canonicalPalace(name: unknown): CanonicalPalace {
  return typeof name === "string" ? PALACE_ALIASES[name] ?? PALACE_ALIASES[name.toLowerCase()] ?? "unknown" : "unknown"
}

function canonicalMajorStar(name: unknown): MajorStarId | null {
  return typeof name === "string" ? MAJOR_STAR_ALIASES[name] ?? MAJOR_STAR_ALIASES[name.toLowerCase()] ?? null : null
}

function canonicalMutagen(value: unknown): MutagenId | null {
  return typeof value === "string" ? MUTAGEN_ALIASES[value] ?? null : null
}

function localeForChart(chart: IFunctionalAstrolabe): ConsumerLocale {
  return chart.palaces.some((palace) => /[\u3400-\u9fff]/u.test(String(palace.name))) ? "zh" : "en"
}

function localized(label: { zh: string; en: string }, locale: ConsumerLocale): string {
  return label[locale]
}

function allStars(palace: IFunctionalPalace) {
  return [...(palace.majorStars ?? []), ...(palace.minorStars ?? []), ...(palace.adjectiveStars ?? [])]
}

function distributionBins(distribution: unknown): ZiweiHistogramBin[] {
  if (Array.isArray(distribution)) {
    if (distribution.every((item) => typeof item === "number" && Number.isFinite(item))) {
      return distribution.map((value) => ({ value, weight: 1 }))
    }
    return distribution.flatMap((item) => {
      const record = asRecord(item)
      const value = asFiniteNumber(record?.value)
      const weight = asFiniteNumber(record?.weight) ?? asFiniteNumber(record?.count)
      return value !== null && weight !== null && weight > 0 ? [{ value, weight }] : []
    })
  }
  const record = asRecord(distribution)
  if (!record) return []
  if (Array.isArray(record.bins)) return distributionBins(record.bins)
  if (Array.isArray(record.histogram)) return distributionBins(record.histogram)
  if (Array.isArray(record.values)) {
    const weights = Array.isArray(record.weights) ? record.weights : []
    return record.values.flatMap((value, index) => {
      const numericValue = asFiniteNumber(value)
      const numericWeight = asFiniteNumber(weights[index]) ?? 1
      return numericValue !== null && numericWeight > 0 ? [{ value: numericValue, weight: numericWeight }] : []
    })
  }
  return Object.entries(record).flatMap(([value, weight]) => {
    const numericValue = Number(value)
    const numericWeight = asFiniteNumber(weight)
    return Number.isFinite(numericValue) && numericWeight !== null && numericWeight > 0 ? [{ value: numericValue, weight: numericWeight }] : []
  })
}

export function rankZiweiScore(rawScore: number, distribution?: ZiweiScoreDistribution | unknown, options: { key?: ZiweiScoreKey; cohort_id?: string; scope?: "global" | "cohort" } = {}): ZiweiRankResult {
  const raw = clamp(rawScore)
  const bins = distributionBins(distribution)
  let percentile: number
  let source: RankSource
  let sampleWeight: number | null
  if (bins.length > 0) {
    const total = bins.reduce((sum, bin) => sum + bin.weight, 0)
    const lower = bins.reduce((sum, bin) => sum + (bin.value < raw ? bin.weight : 0), 0)
    const same = bins.reduce((sum, bin) => sum + (Math.abs(bin.value - raw) < 1e-9 ? bin.weight : 0), 0)
    percentile = total > 0 ? ((lower + same * 0.5) / total) * 100 : 50
    source = "empirical_baseline"
    sampleWeight = round1(total)
  } else {
    const key = options.key ?? "overall"
    const cohortShift = options.scope === "cohort" ? (stableHash(options.cohort_id ?? "all") % 9) - 4 : 0
    const center = FALLBACK_CENTERS[key] + cohortShift
    percentile = 100 / (1 + Math.exp(-(raw - center) / 11.5))
    source = "deterministic_fallback"
    sampleWeight = null
  }
  const normalizedPercentile = round1(clamp(percentile))
  const topPercentage = round1(clamp(100 - normalizedPercentile))
  return {
    raw_score: round1(raw),
    score: round1(raw),
    percentile: normalizedPercentile,
    top_percentage: topPercentage,
    global_percentile: normalizedPercentile,
    global_top_percentage: topPercentage,
    source,
    sample_weight: sampleWeight,
  }
}

function baselineCandidate(value: unknown): ZiweiConsumerBaseline | null {
  const record = asRecord(value)
  if (!record) return null
  const histograms = asRecord(record.histograms) ?? asRecord(record.score_histograms)
  const cohorts = asRecord(record.cohort_histograms) ?? asRecord(record.cohorts)
  const families = Array.isArray(record.structural_families) ? record.structural_families : Array.isArray(record.families) ? record.families : []
  if (!histograms && !cohorts && families.length === 0) return null
  return {
    id: typeof record.id === "string" ? record.id : "ziwei-consumer-baseline",
    histograms: (histograms ?? {}) as ZiweiConsumerBaseline["histograms"],
    cohort_histograms: (cohorts ?? {}) as ZiweiConsumerBaseline["cohort_histograms"],
    structural_families: families as ZiweiStructuralFamilyBaseline[],
    hash: typeof record.hash === "string" ? record.hash : undefined,
    method: typeof record.method === "string" ? record.method : undefined,
  }
}

function globalDistribution(baseline: ZiweiConsumerBaseline | null, key: ZiweiScoreKey): ZiweiScoreDistribution | undefined {
  if (!baseline) return undefined
  const direct = baseline.histograms[key]
  if (direct) return direct
  const histograms = baseline.histograms as unknown
  const nested = asRecord(asRecord(histograms)?.global) ?? asRecord(asRecord(histograms)?.scores)
  return nested?.[key] as ZiweiScoreDistribution | undefined
}

function extractConsumerBaseline(statistics: unknown): ZiweiConsumerBaseline | null {
  const root = asRecord(statistics)
  if (!root) return null
  const baselineRecord = asRecord(root.baseline)
  const candidates = [
    root.consumer_baseline,
    root.consumer,
    baselineRecord?.consumer_baseline,
    baselineRecord?.consumer,
    statistics,
  ]
  for (const candidate of candidates) {
    const baseline = baselineCandidate(candidate)
    if (baseline) return baseline
  }
  return null
}

type RarityMetricSnapshot = { percentage: number; level: string }

function extractRarityMetrics(statistics: unknown): Map<string, RarityMetricSnapshot> {
  const result = new Map<string, RarityMetricSnapshot>()
  const metrics = asRecord(statistics)?.rarity_metrics
  if (!Array.isArray(metrics)) return result
  metrics.forEach((item) => {
    const record = asRecord(item)
    const featureId = typeof record?.feature_id === "string" ? record.feature_id : null
    const percentage = asFiniteNumber(record?.percentage)
    if (featureId && percentage !== null) result.set(featureId, { percentage: clamp(percentage), level: typeof record?.level === "string" ? record.level : "" })
  })
  return result
}

function cohortDistribution(baseline: ZiweiConsumerBaseline | null, cohortId: string, key: ZiweiScoreKey): ZiweiScoreDistribution | undefined {
  if (!baseline) return undefined
  const aliases = [cohortId, `ziwei.${cohortId}`, cohortId.replace(/^life_combo\./, "")]
  for (const alias of aliases) {
    const distribution = baseline.cohort_histograms[alias]?.[key]
    if (distribution) return distribution
  }
  const byScore = asRecord(baseline.cohort_histograms[key])
  return aliases.map((alias) => byScore?.[alias]).find(Boolean) as ZiweiScoreDistribution | undefined
}

export function rankZiweiGlobalScore(rawScore: number, key: ZiweiScoreKey, baseline?: ZiweiConsumerBaseline | null): ZiweiRankResult {
  return rankZiweiScore(rawScore, globalDistribution(baseline ?? null, key), { key, scope: "global" })
}

export function rankZiweiCohortScore(rawScore: number, key: ZiweiScoreKey, cohortId: string, baseline?: ZiweiConsumerBaseline | null): ZiweiRankResult {
  return rankZiweiScore(rawScore, cohortDistribution(baseline ?? null, cohortId, key), { key, cohort_id: cohortId, scope: "cohort" })
}

type StarPlacement = {
  palace: IFunctionalPalace
  palace_id: CanonicalPalace
  palace_index: number
  raw_name: string
  major_id: MajorStarId | null
  auspicious_id: string | null
  challenging_id: string | null
  mutagen_id: MutagenId | null
  brightness: number
}

type ChartContext = {
  chart: IFunctionalAstrolabe
  locale: ConsumerLocale
  life_palace: IFunctionalPalace
  body_palace: IFunctionalPalace
  placements: StarPlacement[]
  life_major_ids: MajorStarId[]
  life_combo_id: string
  cohort_id: string
  feature_ids: string[]
  natal_scores: Record<ZiweiScoreKey, number>
}

function canonicalAnyStar(name: unknown): string | null {
  if (typeof name !== "string") return null
  const normalized = name.toLowerCase()
  return canonicalMajorStar(name) ?? AUSPICIOUS_ALIASES[name] ?? AUSPICIOUS_ALIASES[normalized] ?? CHALLENGING_ALIASES[name] ?? CHALLENGING_ALIASES[normalized] ?? normalized
}

function findPalace(chart: IFunctionalAstrolabe, palaceId: CanonicalPalace): IFunctionalPalace | undefined {
  return chart.palaces.find((palace) => canonicalPalace(palace.name) === palaceId)
}

function palaceWeights(chart: IFunctionalAstrolabe, key: ZiweiScoreKey): Map<number, number> {
  const result = new Map<number, number>()
  const byIndex = new Map(chart.palaces.map((palace) => [palace.index, palace]))
  const add = (index: number, weight: number) => result.set(index, Math.max(result.get(index) ?? 0, weight))
  THEME_PRIMARY_PALACES[key].forEach((palaceId, primaryIndex) => {
    const palace = findPalace(chart, palaceId)
    if (!palace) return
    add(palace.index, primaryIndex === 0 ? 1 : 0.72)
    ;[[4, 0.42], [6, 0.34], [8, 0.42]].forEach(([offset, weight]) => {
      const related = byIndex.get((palace.index + offset) % 12)
      if (related) add(related.index, weight * (primaryIndex === 0 ? 1 : 0.8))
    })
  })
  return result
}

function buildPlacements(chart: IFunctionalAstrolabe): StarPlacement[] {
  return chart.palaces.flatMap((palace) => allStars(palace).map((star) => {
    const rawName = String(star.name)
    return {
      palace,
      palace_id: canonicalPalace(palace.name),
      palace_index: palace.index,
      raw_name: rawName,
      major_id: canonicalMajorStar(rawName),
      auspicious_id: AUSPICIOUS_ALIASES[rawName] ?? AUSPICIOUS_ALIASES[rawName.toLowerCase()] ?? null,
      challenging_id: CHALLENGING_ALIASES[rawName] ?? CHALLENGING_ALIASES[rawName.toLowerCase()] ?? null,
      mutagen_id: canonicalMutagen(star.mutagen),
      brightness: BRIGHTNESS_ADJUSTMENT[String(star.brightness ?? "")] ?? 0,
    }
  }))
}

function scoreNatalTheme(chart: IFunctionalAstrolabe, placements: StarPlacement[], key: ZiweiScoreKey): number {
  const weights = palaceWeights(chart, key)
  let score = key === "overall" ? 41 : 42
  placements.forEach((placement) => {
    const palaceWeight = weights.get(placement.palace_index) ?? 0
    if (palaceWeight <= 0) return
    if (placement.major_id) score += MAJOR_THEME_VECTORS[placement.major_id][key] * (1 + placement.brightness) * palaceWeight
    if (placement.auspicious_id) score += 1.55 * palaceWeight
    if (placement.challenging_id) score -= 1.7 * palaceWeight
    if (placement.mutagen_id) score += MUTAGEN_THEME_VECTORS[placement.mutagen_id][key] * palaceWeight
  })

  const bodyPalace = chart.palaces.find((palace) => palace.isBodyPalace)
  if (bodyPalace) score += 2.2 * (weights.get(bodyPalace.index) ?? 0)

  const relevant = placements.filter((placement) => (weights.get(placement.palace_index) ?? 0) > 0)
  const supportIds = new Set(relevant.flatMap((placement) => placement.auspicious_id ? [placement.auspicious_id] : []))
  const challengeIds = new Set(relevant.flatMap((placement) => placement.challenging_id ? [placement.challenging_id] : []))
  const supportPalaces = new Set(relevant.flatMap((placement) => placement.auspicious_id ? [placement.palace_index] : []))
  const challengePalaces = new Set(relevant.flatMap((placement) => placement.challenging_id ? [placement.palace_index] : []))
  const maxChallengeDensity = Math.max(0, ...chart.palaces.map((palace) => relevant.filter((placement) => placement.palace_index === palace.index && placement.challenging_id).length))
  score += Math.min(2.4, supportIds.size * 0.35 + supportPalaces.size * 0.18)
  score -= Math.min(2.7, challengeIds.size * 0.32 + challengePalaces.size * 0.16 + Math.max(0, maxChallengeDensity - 1) * 0.35)

  const primaryPalace = findPalace(chart, THEME_PRIMARY_PALACES[key][0])
  if (primaryPalace && primaryPalace.majorStars.length === 0) {
    const borrowedStrength = [4, 6, 8].reduce((sum, offset) => {
      const relatedWeight = weights.get((primaryPalace.index + offset) % 12) ?? 0
      return sum + placements.filter((placement) => placement.palace_index === (primaryPalace.index + offset) % 12 && placement.major_id).reduce((value, placement) => value + (2 + placement.brightness) * relatedWeight, 0)
    }, 0)
    score += Math.min(3.2, borrowedStrength * 0.35)
  }
  return round1(clamp(score, 18, 92))
}

function branchFeatureId(palace: IFunctionalPalace): string {
  const rawBranch = String(palace.earthlyBranch).toLowerCase().replace(/\s+/g, "-")
  return `ziwei.body_branch.${EARTHLY_BRANCH_IDS[String(palace.earthlyBranch)] ?? (rawBranch || "unknown")}`
}

function buildFeatureIds(chart: IFunctionalAstrolabe, placements: StarPlacement[], lifeMajorIds: MajorStarId[], bodyPalace: IFunctionalPalace): string[] {
  const result = [`ziwei.life_combo.${lifeMajorIds.join("-") || "empty"}`, branchFeatureId(bodyPalace)]
  const brightnessCounts = new Map<string, number>()
  const brightnessNames: Record<string, string> = { 庙: "miao", 廟: "miao", "[+3]": "miao", 旺: "wang", "[+2]": "wang", 得: "de", "[+1]": "de", 利: "li", "[0]": "li", 平: "ping", "[-1]": "ping", 不: "unmarked", "[-2]": "unmarked", 陷: "xian", "[-3]": "xian" }
  chart.palaces.forEach((palace) => palace.majorStars.forEach((star) => {
    const slug = brightnessNames[String(star.brightness ?? "")] ?? "unmarked"
    brightnessCounts.set(slug, (brightnessCounts.get(slug) ?? 0) + 1)
  }))
  brightnessCounts.forEach((count, name) => result.push(`ziwei.brightness.${name}.${count}`))
  placements.forEach((placement) => {
    if (placement.mutagen_id) result.push(`ziwei.mutagen.${placement.mutagen_id}.palace-${placement.palace_index}`)
  })
  const supportDensity = chart.palaces.map((palace) => placements.filter((placement) => placement.palace_index === palace.index && placement.auspicious_id).length)
  const challengeDensity = chart.palaces.map((palace) => placements.filter((placement) => placement.palace_index === palace.index && placement.challenging_id).length)
  result.push(`ziwei.auspicious_palaces.${supportDensity.filter(Boolean).length}`)
  result.push(`ziwei.auspicious_max_density.${Math.max(0, ...supportDensity)}`)
  result.push(`ziwei.challenging_palaces.${challengeDensity.filter(Boolean).length}`)
  result.push(`ziwei.challenging_max_density.${Math.max(0, ...challengeDensity)}`)
  result.push(`ziwei.empty_palaces.${chart.palaces.filter((palace) => palace.majorStars.length === 0).length}`)
  return [...new Set(result)]
}

function chartContext(chart: IFunctionalAstrolabe): ChartContext {
  const lifePalace = findPalace(chart, "life") ?? chart.palaces[0]
  const bodyPalace = chart.palaces.find((palace) => palace.isBodyPalace) ?? lifePalace
  const placements = buildPlacements(chart)
  const lifeMajorIds = lifePalace.majorStars.flatMap((star) => {
    const id = canonicalMajorStar(star.name)
    return id ? [id] : []
  }).sort()
  const lifeComboId = lifeMajorIds.join("-") || "empty"
  const natalScores = Object.fromEntries(SCORE_KEYS.map((key) => [key, scoreNatalTheme(chart, placements, key)])) as Record<ZiweiScoreKey, number>
  natalScores.overall = round1(clamp(natalScores.overall * 0.48 + natalScores.career * 0.17 + natalScores.wealth * 0.13 + natalScores.relationship * 0.11 + natalScores.health * 0.11, 18, 92))
  return {
    chart,
    locale: localeForChart(chart),
    life_palace: lifePalace,
    body_palace: bodyPalace,
    placements,
    life_major_ids: lifeMajorIds,
    life_combo_id: lifeComboId,
    cohort_id: `life_combo.${lifeComboId}`,
    feature_ids: buildFeatureIds(chart, placements, lifeMajorIds, bodyPalace),
    natal_scores: natalScores,
  }
}

/**
 * Small, side-effect-free projection used by the offline baseline generator.
 * It intentionally excludes horoscope/K-line work so the generator can
 * aggregate hundreds of thousands of natal states without retaining samples.
 */
export function computeZiweiNatalConsumerScores(chart: IFunctionalAstrolabe): {
  scores: Record<ZiweiScoreKey, number>
  cohort_id: string
  achievement_feature_ids: string[]
  archetype: {
    id: ZiweiArchetypeId
    title: string
    title_en: string
    summary: string
    summary_en: string
  }
} {
  const context = chartContext(chart)
  const archetype = selectArchetype(context)
  return {
    scores: { ...context.natal_scores },
    cohort_id: context.cohort_id,
    achievement_feature_ids: achievementFeatureIds(context),
    archetype: {
      id: archetype.id,
      title: archetype.title,
      title_en: archetype.title_en,
      summary: archetype.headline,
      summary_en: archetype.headline_en,
    },
  }
}

function palaceAffinity(key: ZiweiThemeKey, palace: CanonicalPalace): number {
  const primary = THEME_PRIMARY_PALACES[key]
  if (palace === primary[0]) return 1
  if (palace === primary[1]) return 0.72
  const secondary: Record<ZiweiThemeKey, Partial<Record<CanonicalPalace, number>>> = {
    career: { travel: 0.55, friends: 0.42, wealth: 0.32 },
    wealth: { career: 0.48, spirit: 0.4, travel: 0.28 },
    relationship: { children: 0.62, friends: 0.48, life: 0.35 },
    health: { life: 0.55, parents: 0.3, travel: 0.24 },
  }
  return secondary[key][palace] ?? 0.12
}

type PeriodImpact = { value: number; intensity: number; drivers: string[] }

function periodItemImpact(context: ChartContext, item: HoroscopeItem | undefined, key: ZiweiThemeKey, scopeWeight: number): PeriodImpact {
  if (!item) return { value: 0, intensity: 0, drivers: [] }
  let value = 0
  let intensity = 0
  const drivers: string[] = []
  const palaceNames = item.palaceNames ?? []
  ;(item.stars ?? []).forEach((stars, index) => {
    const palace = canonicalPalace(palaceNames[index])
    const affinity = palaceAffinity(key, palace)
    stars.forEach((star) => {
      const type = String(star.type)
      let effect = 0
      if (type === "soft" || type === "helper") effect = 0.75
      else if (type === "lucun") effect = key === "wealth" ? 1.25 : 0.65
      else if (type === "tianma") effect = key === "career" || key === "wealth" ? 0.65 : 0.2
      else if (type === "flower") effect = key === "relationship" ? 0.9 : 0.2
      else if (type === "tough") effect = -0.95
      if (effect === 0) return
      value += effect * affinity * scopeWeight
      intensity += Math.abs(effect) * affinity * scopeWeight
      if (affinity >= 0.7 && drivers.length < 3) drivers.push(String(star.name))
    })
  })
  if (typeof item.index === "number") {
    const activePalace = canonicalPalace(palaceNames[item.index])
    const affinity = palaceAffinity(key, activePalace)
    value += 0.7 * affinity * scopeWeight
    intensity += affinity * scopeWeight
  }
  ;(item.mutagen ?? []).forEach((starName, mutagenIndex) => {
    const mutagen = (["lu", "quan", "ke", "ji"] as const)[mutagenIndex]
    if (!mutagen) return
    const starId = canonicalAnyStar(starName)
    const placement = context.placements.find((candidate) => canonicalAnyStar(candidate.raw_name) === starId)
    if (!placement) return
    const assignedPalace = canonicalPalace(palaceNames[placement.palace_index])
    const affinity = Math.max(palaceAffinity(key, assignedPalace), palaceAffinity(key, placement.palace_id) * 0.7)
    const effect = MUTAGEN_THEME_VECTORS[mutagen][key] * 0.42 * affinity * scopeWeight
    value += effect
    intensity += Math.abs(effect)
    if (affinity >= 0.7 && drivers.length < 3) drivers.push(`${String(starName)}·${localized(MUTAGEN_LABELS[mutagen], context.locale)}`)
  })
  return { value, intensity, drivers: [...new Set(drivers)] }
}

function horoscopeImpact(context: ChartContext, horoscope: IFunctionalHoroscope | null | undefined, key: ZiweiThemeKey): PeriodImpact {
  if (!horoscope) return { value: 0, intensity: 0, drivers: [] }
  const impacts = [
    periodItemImpact(context, horoscope.decadal, key, 0.35),
    periodItemImpact(context, horoscope.yearly, key, 0.65),
    periodItemImpact(context, horoscope.monthly, key, 1),
  ]
  return {
    value: round1(clamp(impacts.reduce((sum, impact) => sum + impact.value, 0), -7, 7)),
    intensity: round1(impacts.reduce((sum, impact) => sum + impact.intensity, 0)),
    drivers: [...new Set(impacts.flatMap((impact) => impact.drivers))].slice(0, 5),
  }
}

function periodAdjustedScores(context: ChartContext, horoscope: IFunctionalHoroscope | null | undefined): { scores: Record<ZiweiScoreKey, number>; impacts: Record<ZiweiThemeKey, PeriodImpact> } {
  const impacts = Object.fromEntries(SUBJECT_KEYS.map((key) => [key, horoscopeImpact(context, horoscope, key)])) as Record<ZiweiThemeKey, PeriodImpact>
  const scores = { ...context.natal_scores }
  SUBJECT_KEYS.forEach((key) => { scores[key] = round1(clamp(scores[key] + impacts[key].value)) })
  scores.overall = round1(clamp(context.natal_scores.overall * 0.5 + scores.career * 0.17 + scores.wealth * 0.13 + scores.relationship * 0.1 + scores.health * 0.1))
  return { scores, impacts }
}

function lifeNetworkIndices(context: ChartContext): Set<number> {
  return new Set([0, 4, 6, 8].map((offset) => (context.life_palace.index + offset) % 12))
}

function selectArchetype(context: ChartContext): ZiweiArchetype {
  const network = lifeNetworkIndices(context)
  const networkPlacements = context.placements.filter((placement) => network.has(placement.palace_index))
  const bodyMajorIds = context.body_palace.majorStars.flatMap((star) => {
    const id = canonicalMajorStar(star.name)
    return id ? [id] : []
  })
  const supportCount = new Set(networkPlacements.flatMap((placement) => placement.auspicious_id ? [placement.auspicious_id] : [])).size
  const ranked = ZIWEI_ARCHETYPES.map((archetype, order) => {
    let score = 0
    if (archetype.anchor_star) {
      const lifePlacement = context.placements.find((placement) => placement.palace_index === context.life_palace.index && placement.major_id === archetype.anchor_star)
      const networkPlacement = networkPlacements.find((placement) => placement.major_id === archetype.anchor_star)
      score = lifePlacement ? 82 + lifePlacement.brightness * 14 : networkPlacement ? 40 + networkPlacement.brightness * 8 : 4
      if (canonicalMajorStar(context.chart.body) === archetype.anchor_star) score += 5
    } else if (archetype.id === "stellar-duet") {
      score = context.life_major_ids.length >= 2 ? 88 + Math.min(4, context.life_major_ids.length) : 8
    } else if (archetype.id === "borrowed-axis") {
      score = context.life_major_ids.length === 0 ? 102 : 3
    } else if (archetype.id === "six-aids-network") {
      score = supportCount >= 5 ? 94 + supportCount : supportCount * 9
    } else if (archetype.id === "dual-track") {
      const disjoint = bodyMajorIds.length > 0 && bodyMajorIds.every((star) => !context.life_major_ids.includes(star))
      score = context.body_palace.index !== context.life_palace.index && disjoint ? 79 : 5
    }
    return { archetype, score, order }
  })
  ranked.sort((left, right) => right.score - left.score || left.order - right.order)
  return ranked[0].archetype
}

function achievementFeatureIds(context: ChartContext): string[] {
  const network = lifeNetworkIndices(context)
  const networkPlacements = context.placements.filter((placement) => network.has(placement.palace_index))
  const networkStars = new Set(networkPlacements.flatMap((placement) => [placement.major_id, placement.auspicious_id].filter((value): value is string => Boolean(value))))
  const ids: string[] = []
  const addPair = (id: string, members: [string, string]) => {
    if (members.every((member) => networkStars.has(member))) ids.push(`ziwei.achievement.${id}`)
  }
  addPair("ziwei-tianfu", ["ziwei", "tianfu"])
  addPair("sun-moon", ["taiyang", "taiyin"])
  addPair("left-right", ["zuofu", "youbi"])
  addPair("chang-qu", ["wenchang", "wenqu"])
  addPair("kui-yue", ["tiankui", "tianyue"])
  addPair("sha-po-lang", ["qisha", "pojun"])
  if (new Set(networkPlacements.flatMap((placement) => placement.mutagen_id && placement.mutagen_id !== "ji" ? [placement.mutagen_id] : [])).size >= 3) ids.push("ziwei.achievement.three-positive-transformations")
  if (new Set(networkPlacements.flatMap((placement) => placement.auspicious_id ? [placement.auspicious_id] : [])).size >= 4) ids.push("ziwei.achievement.six-aids-network")
  if (context.body_palace.index === context.life_palace.index) ids.push("ziwei.achievement.life-body-aligned")
  if (networkPlacements.some((placement) => placement.mutagen_id === "ji")) ids.push("ziwei.achievement.main-axis-obstacle")
  if (ids.length === 0) ids.push("ziwei.achievement.life-axis-defined")
  return ids
}

type FingerprintCandidate = {
  id: string
  family: string
  feature_id: string
  title: string
  detail: string
  salience: number
}

function rarityLabel(percentage: number, locale: ConsumerLocale): string {
  if (percentage <= 2) return locale === "zh" ? "极少见" : "Ultra rare"
  if (percentage <= 8) return locale === "zh" ? "少见" : "Rare"
  if (percentage <= 20) return locale === "zh" ? "鲜明" : "Distinctive"
  return locale === "zh" ? "可辨识" : "Recognizable"
}

function featurePercentage(featureId: string, rarityMetrics: Map<string, RarityMetricSnapshot>, fallback: number): number {
  const direct = rarityMetrics.get(featureId)
  if (direct) return round1(clamp(direct.percentage, 0.1, 100))
  const prefix = [...rarityMetrics.entries()].find(([candidate]) => candidate.startsWith(featureId) || featureId.startsWith(candidate))?.[1]
  return round1(clamp(prefix?.percentage ?? fallback, 0.1, 100))
}

function buildFingerprints(context: ChartContext, horoscope: IFunctionalHoroscope | null | undefined, rarityMetrics: Map<string, RarityMetricSnapshot>): ZiweiConsumerFingerprint[] {
  const locale = context.locale
  const lifeLabels = context.life_major_ids.map((id) => localized(MAJOR_STAR_LABELS[id], locale))
  const candidates: FingerprintCandidate[] = [{
    id: `life-${context.life_combo_id}`,
    family: "life-axis",
    feature_id: `ziwei.life_combo.${context.life_combo_id}`,
    title: locale === "zh" ? `命宫主轴 · ${lifeLabels.join("×") || "空宫借星"}` : `Life axis · ${lifeLabels.join(" × ") || "Borrowed stars"}`,
    detail: locale === "zh" ? "这是整张盘最稳定的身份底色。" : "This is the chart's most stable identity signature.",
    salience: 100,
  }, {
    id: `body-${context.body_palace.index}`,
    family: "body-axis",
    feature_id: branchFeatureId(context.body_palace),
    title: locale === "zh" ? `身宫落${localized(PALACE_LABELS[canonicalPalace(context.body_palace.name)], locale)}` : `Body palace · ${localized(PALACE_LABELS[canonicalPalace(context.body_palace.name)], locale)}`,
    detail: locale === "zh" ? "真实行动会反复回到这个人生场域。" : "Lived action repeatedly returns to this arena.",
    salience: context.body_palace.index === context.life_palace.index ? 86 : 72,
  }]

  context.placements.filter((placement) => placement.mutagen_id).forEach((placement) => {
    const mutagen = placement.mutagen_id as MutagenId
    const starLabel = placement.major_id ? localized(MAJOR_STAR_LABELS[placement.major_id], locale) : placement.raw_name
    const palaceLabel = localized(PALACE_LABELS[placement.palace_id], locale)
    candidates.push({
      id: `mutagen-${mutagen}-${placement.palace_index}`,
      family: "natal-transformations",
      feature_id: `ziwei.mutagen.${mutagen}.palace-${placement.palace_index}`,
      title: locale === "zh" ? `${starLabel}${localized(MUTAGEN_LABELS[mutagen], locale)} · ${palaceLabel}` : `${starLabel} ${localized(MUTAGEN_LABELS[mutagen], locale)} · ${palaceLabel}`,
      detail: mutagen === "ji" ? (locale === "zh" ? "高压点很明确，越早设边界越有主动权。" : "The pressure point is explicit; early boundaries restore agency.") : (locale === "zh" ? "这条四化链会放大对应主题的可见度。" : "This transformation amplifies the theme's visibility."),
      salience: mutagen === "ji" ? 93 : mutagen === "lu" ? 91 : mutagen === "quan" ? 88 : 84,
    })
  })

  const supportPlacements = context.placements.filter((placement) => placement.auspicious_id)
  const challengePlacements = context.placements.filter((placement) => placement.challenging_id)
  const supportIds = [...new Set(supportPlacements.flatMap((placement) => placement.auspicious_id ? [placement.auspicious_id] : []))]
  const challengeIds = [...new Set(challengePlacements.flatMap((placement) => placement.challenging_id ? [placement.challenging_id] : []))]
  const supportPalaceCount = new Set(supportPlacements.map((placement) => placement.palace_index)).size
  const challengePalaceCount = new Set(challengePlacements.map((placement) => placement.palace_index)).size
  candidates.push({
    id: `six-aids-${supportIds.length}-${supportPalaceCount}`,
    family: "six-aids",
    feature_id: `ziwei.auspicious_palaces.${supportPalaceCount}`,
    title: locale === "zh" ? `六吉星网络 · ${supportIds.length}/6` : `Six-aids network · ${supportIds.length}/6`,
    detail: locale === "zh" ? `助力分布在 ${supportPalaceCount} 个宫位，${supportIds.map((id) => AUSPICIOUS_LABELS[id]?.zh).filter(Boolean).join("、") || "尚未成网"}。` : `Support spans ${supportPalaceCount} palaces: ${supportIds.map((id) => AUSPICIOUS_LABELS[id]?.en).filter(Boolean).join(", ") || "not yet networked"}.`,
    salience: 52 + supportIds.length * 5,
  }, {
    id: `six-challenges-${challengeIds.length}-${challengePalaceCount}`,
    family: "six-challenges",
    feature_id: `ziwei.challenging_palaces.${challengePalaceCount}`,
    title: locale === "zh" ? `六煞星张力 · ${challengeIds.length}/6` : `Six-challenge tension · ${challengeIds.length}/6`,
    detail: locale === "zh" ? `张力落在 ${challengePalaceCount} 个宫位（${challengeIds.map((id) => CHALLENGING_LABELS[id]?.zh).filter(Boolean).join("、") || "未成组"}）；分散可转为推动力，集中则先做减压。` : `Tension spans ${challengePalaceCount} palaces (${challengeIds.map((id) => CHALLENGING_LABELS[id]?.en).filter(Boolean).join(", ") || "not grouped"}); spread can propel, concentration needs relief.`,
    salience: 48 + challengeIds.length * 5,
  })

  const brightMajorCount = context.placements.filter((placement) => placement.major_id && placement.brightness >= 0.2).length
  candidates.push({
    id: `bright-major-${brightMajorCount}`,
    family: "brightness",
    feature_id: `ziwei.brightness.miao.${context.placements.filter((placement) => placement.major_id && placement.brightness >= 0.28).length}`,
    title: locale === "zh" ? `高亮主星 · ${brightMajorCount} 颗` : `High-brightness majors · ${brightMajorCount}`,
    detail: locale === "zh" ? "庙旺主星决定哪些能力更容易直接兑现。" : "Strong-brightness majors show what converts most directly.",
    salience: 45 + brightMajorCount * 4,
  })
  if (horoscope?.monthly) candidates.push({
    id: `monthly-${horoscope.monthly.heavenlyStem}-${horoscope.monthly.earthlyBranch}`,
    family: "selected-period",
    feature_id: `ziwei.period.monthly.${String(horoscope.monthly.heavenlyStem)}${String(horoscope.monthly.earthlyBranch)}`,
    title: locale === "zh" ? `当前流月 · ${horoscope.monthly.heavenlyStem}${horoscope.monthly.earthlyBranch}` : `Selected month · ${horoscope.monthly.heavenlyStem}${horoscope.monthly.earthlyBranch}`,
    detail: locale === "zh" ? "这是当前时段的放大镜，不会改写本命底盘。" : "This magnifies the selected period without rewriting the natal base.",
    salience: 44,
  })

  const seenFamilies = new Set<string>()
  return candidates.sort((left, right) => right.salience - left.salience || left.id.localeCompare(right.id)).filter((candidate) => {
    if (seenFamilies.has(candidate.family)) return false
    seenFamilies.add(candidate.family)
    return true
  }).slice(0, 5).map((candidate) => {
    const fallback = clamp(42 - candidate.salience * 0.36, 1.2, 38)
    const percentage = featurePercentage(candidate.feature_id, rarityMetrics, fallback)
    return { id: candidate.id, title: candidate.title, detail: candidate.detail, rarity_label: rarityLabel(percentage, locale), top_percentage: percentage }
  })
}

type AchievementCandidate = Omit<ZiweiConsumerAchievement, "tier" | "rarity_percentage"> & { fallback_percentage: number; feature_id: string }

function achievementTier(percentage: number): "SSR" | "SR" | "R" {
  return percentage <= 2 ? "SSR" : percentage <= 8 ? "SR" : "R"
}

function buildAchievements(context: ChartContext, rarityMetrics: Map<string, RarityMetricSnapshot>): ZiweiConsumerAchievement[] {
  const locale = context.locale
  const network = lifeNetworkIndices(context)
  const networkPlacements = context.placements.filter((placement) => network.has(placement.palace_index))
  const networkStars = new Set(networkPlacements.flatMap((placement) => [placement.major_id, placement.auspicious_id].filter((value): value is string => Boolean(value))))
  const candidates: AchievementCandidate[] = []
  const addPair = (id: string, members: [string, string], zh: string, en: string, fallback: number) => {
    if (!members.every((member) => networkStars.has(member))) return
    candidates.push({ id, title: locale === "zh" ? zh : en, state: "有力", position: locale === "zh" ? "命宫三方四正" : "Life-palace network", summary: locale === "zh" ? "两颗关键星在主轴网络内完成呼应。" : "Two key stars echo inside the life-axis network.", member_ids: members, fallback_percentage: fallback, feature_id: `ziwei.achievement.${id}` })
  }
  addPair("ziwei-tianfu", ["ziwei", "tianfu"], "紫府同轴", "Emperor–Empress axis", 3.2)
  addPair("sun-moon", ["taiyang", "taiyin"], "日月并明", "Sun–Moon resonance", 5.8)
  addPair("left-right", ["zuofu", "youbi"], "左右同援", "Officer–Helper support", 7.2)
  addPair("chang-qu", ["wenchang", "wenqu"], "昌曲同频", "Scholar–Artist resonance", 6.4)
  addPair("kui-yue", ["tiankui", "tianyue"], "魁钺夹持", "Assistant–Aide support", 5.9)
  addPair("sha-po-lang", ["qisha", "pojun"], "杀破先锋", "Marshal–Rebel vanguard", 4.6)

  const positiveMutagens = networkPlacements.filter((placement) => placement.mutagen_id && placement.mutagen_id !== "ji")
  if (new Set(positiveMutagens.map((placement) => placement.mutagen_id)).size >= 3) candidates.push({
    id: "three-positive-transformations", title: locale === "zh" ? "禄权科成链" : "Prosperity–Power–Merit chain", state: "发力", position: locale === "zh" ? "命宫三方四正" : "Life-palace network", summary: locale === "zh" ? "三条正向四化在主轴网络内同时可用。" : "All three constructive transformations are active in the main network.", member_ids: positiveMutagens.map((placement) => placement.raw_name), fallback_percentage: 1.8, feature_id: "ziwei.achievement.three-positive-transformations",
  })
  const supportCount = new Set(networkPlacements.flatMap((placement) => placement.auspicious_id ? [placement.auspicious_id] : [])).size
  if (supportCount >= 4) candidates.push({
    id: "six-aids-network", title: locale === "zh" ? "六曜成网" : "Six-aids network", state: supportCount >= 5 ? "发力" : "有力", position: locale === "zh" ? "命宫三方四正" : "Life-palace network", summary: locale === "zh" ? `${supportCount} 类吉曜进入主轴网络，帮助不是孤点。` : `${supportCount} aid types enter the main network; support is not isolated.`, member_ids: [...networkStars].filter((id) => id in AUSPICIOUS_LABELS), fallback_percentage: supportCount >= 5 ? 1.5 : 4.8, feature_id: "ziwei.achievement.six-aids-network",
  })
  if (context.body_palace.index === context.life_palace.index) candidates.push({
    id: "life-body-aligned", title: locale === "zh" ? "命身同宫" : "Life–Body alignment", state: "有力", position: String(context.life_palace.name), summary: locale === "zh" ? "内在主轴与实际行动落在同一宫位。" : "Inner identity and lived action occupy the same palace.", member_ids: context.life_major_ids, fallback_percentage: 8.3, feature_id: "ziwei.achievement.life-body-aligned",
  })
  const lifeJi = networkPlacements.find((placement) => placement.mutagen_id === "ji")
  if (lifeJi) candidates.push({
    id: "main-axis-obstacle", title: locale === "zh" ? "主轴化忌淬炼" : "Main-axis obstacle forge", state: "受制", position: String(lifeJi.palace.name), summary: locale === "zh" ? "压力点进入主轴网络；把边界做早，反而能变成辨识度。" : "Pressure enters the main network; early boundaries can turn it into distinction.", member_ids: [lifeJi.raw_name], fallback_percentage: 9.6, feature_id: "ziwei.achievement.main-axis-obstacle",
  })
  if (candidates.length === 0) candidates.push({
    id: "life-axis-defined", title: locale === "zh" ? "主轴成形" : "Defined life axis", state: "可见", position: String(context.life_palace.name), summary: locale === "zh" ? "命宫结构已形成稳定、可识别的主轴。" : "The life palace forms a stable, recognizable axis.", member_ids: context.life_major_ids, fallback_percentage: 22, feature_id: "ziwei.achievement.life-axis-defined",
  })
  return candidates.map((candidate) => {
    const percentage = featurePercentage(candidate.feature_id, rarityMetrics, candidate.fallback_percentage)
    return {
      id: candidate.id,
      title: candidate.title,
      state: candidate.state,
      position: candidate.position,
      summary: candidate.summary,
      member_ids: candidate.member_ids,
      tier: achievementTier(percentage),
      rarity_percentage: percentage,
    }
  }).sort((left, right) => ({ SSR: 0, SR: 1, R: 2 })[left.tier] - ({ SSR: 0, SR: 1, R: 2 })[right.tier] || left.id.localeCompare(right.id)).slice(0, 6)
}

function representativeLabel(value: string | { label?: string; state?: string; date?: string }): string {
  if (typeof value === "string") return value
  return value.label ?? value.state ?? value.date ?? "Representative state"
}

function buildTwin(context: ChartContext, archetype: ZiweiArchetype, baseline: ZiweiConsumerBaseline | null, rarityMetrics: Map<string, RarityMetricSnapshot>): ZiweiStructuralTwin {
  const locale = context.locale
  const currentFeatures = new Set([
    ...context.feature_ids,
    `archetype:${archetype.id}`,
    `life:${context.life_combo_id}`,
    `body:${canonicalPalace(context.body_palace.name)}`,
  ])
  const matches = (baseline?.structural_families ?? []).map((family) => {
    const features = new Set(family.features ?? [])
    const intersection = [...features].filter((feature) => currentFeatures.has(feature)).length
    const union = new Set([...features, ...currentFeatures]).size
    const similarity = union > 0 ? intersection / union : 0
    const archetypeBoost = family.archetype_id === archetype.id ? 0.3 : 0
    return { family, similarity: similarity + archetypeBoost }
  }).sort((left, right) => right.similarity - left.similarity || left.family.id.localeCompare(right.family.id))
  const match = matches[0]
  if (match && match.similarity > 0) {
    const family = match.family
    const share = family.share_percentage ?? (family.weight && family.total_weight ? (family.weight / family.total_weight) * 100 : null)
    return {
      family_id: family.id,
      title: locale === "zh" ? family.title : family.title_en ?? family.title,
      share_percentage: round1(clamp(share ?? 8 + (1 - Math.min(1, match.similarity)) * 8, 0.1, 100)),
      summary: locale === "zh" ? family.summary : family.summary_en ?? family.summary,
      representatives: (family.representatives ?? []).map(representativeLabel).slice(0, 3),
    }
  }
  const lifeFeature = `ziwei.life_combo.${context.life_combo_id}`
  const share = featurePercentage(lifeFeature, rarityMetrics, clamp(18 - context.life_major_ids.length * 4 - context.placements.filter((placement) => placement.mutagen_id).length * 0.8, 2.5, 18))
  const lifeLabel = context.life_major_ids.map((id) => localized(MAJOR_STAR_LABELS[id], locale)).join(" × ") || (locale === "zh" ? "空宫借星" : "Borrowed-star life palace")
  const bodyLabel = localized(PALACE_LABELS[canonicalPalace(context.body_palace.name)], locale)
  return {
    family_id: `fallback.${archetype.family}.${context.life_combo_id}`,
    title: locale === "zh" ? `同轴家族 · ${archetype.title}` : `Same-axis family · ${archetype.title_en}`,
    share_percentage: share,
    summary: locale === "zh" ? `命宫主轴与行动落点相近的人，通常共享“${archetype.title}”的决策节奏。` : `Charts with a similar life axis and action placement tend to share the ${archetype.title_en} rhythm.`,
    representatives: locale === "zh" ? [`命宫同轴：${lifeLabel}`, `身宫落点：${bodyLabel}`, `结构家族：${archetype.title}`] : [`Life axis: ${lifeLabel}`, `Body placement: ${bodyLabel}`, `Structural family: ${archetype.title_en}`],
  }
}

const klineCache = new WeakMap<IFunctionalAstrolabe, Map<string, ZiweiLifeKline>>()

function horoscopeYear(horoscope: IFunctionalHoroscope): number | null {
  const match = String(horoscope.solarDate).match(/^(\d{4})[-/]/)
  const value = match ? Number(match[1]) : Number.NaN
  return Number.isInteger(value) ? value : null
}

function safeHoroscope(chart: IFunctionalAstrolabe, selected: IFunctionalHoroscope, year: number, month: number): IFunctionalHoroscope | null {
  if (typeof chart.horoscope === "function") {
    try {
      return chart.horoscope(`${year}-${String(month).padStart(2, "0")}-15`)
    } catch {
      // A static chart snapshot may expose a method without enough normalized input.
    }
  }
  const selectedMatch = String(selected.solarDate).match(/^(\d{4})[-/](\d{1,2})[-/]/)
  return selectedMatch && Number(selectedMatch[1]) === year && Number(selectedMatch[2]) === month ? selected : null
}

function movingAverage(points: ZiweiKlinePoint[], index: number, window: number): number | null {
  if (index + 1 < window) return null
  return round1(points.slice(index + 1 - window, index + 1).reduce((sum, point) => sum + point.close, 0) / window)
}

function mergePeriodBands(yearlyLabels: Array<{ year: number; label: string }>): ZiweiKlinePeriodBand[] {
  const result: ZiweiKlinePeriodBand[] = []
  yearlyLabels.forEach(({ year, label }) => {
    const previous = result[result.length - 1]
    if (previous && previous.label === label && previous.end_year === year - 1) previous.end_year = year
    else result.push({ label, start_year: year, end_year: year })
  })
  return result
}

function emptyKline(year: number | null): ZiweiLifeKline {
  const fallbackYear = year ?? new Date().getUTCFullYear()
  return {
    default_window: { start_year: fallbackYear, end_year: fallbackYear },
    series: SCORE_KEYS.map((key) => ({ key, label: key, color: SCORE_COLORS[key], points: [] })),
    period_bands: [],
    stages: [],
    method: "iztro_monthly_midpoint_annual_ohlcv",
  }
}

function buildZiweiLifeKlineInternal(chart: IFunctionalAstrolabe, horoscope: IFunctionalHoroscope | null | undefined, existingContext?: ChartContext): ZiweiLifeKline {
  if (!horoscope) return emptyKline(null)
  const selectedYear = horoscopeYear(horoscope)
  if (selectedYear === null) return emptyKline(null)
  // The selected horoscope date controls the detail panel, not the chart's
  // viewport. Keep the consumer's ten-year outlook anchored to the current
  // year so clicking a candle never silently shifts the whole window.
  const startYear = Math.max(1900, Math.min(new Date().getFullYear(), 2098))
  const endYear = Math.min(2100, startYear + 9)
  const cacheKey = `${startYear}-${endYear}`
  const chartCache = klineCache.get(chart)
  const cached = chartCache?.get(cacheKey)
  if (cached) return cached

  const context = existingContext ?? chartContext(chart)
  const labels: Record<ZiweiScoreKey, string> = {
    overall: context.locale === "zh" ? "综合" : "Overall",
    career: context.locale === "zh" ? "事业" : "Career",
    wealth: context.locale === "zh" ? "财富" : "Wealth",
    relationship: context.locale === "zh" ? "感情" : "Relationships",
    health: context.locale === "zh" ? "健康" : "Health",
  }
  const monthlyByKey = Object.fromEntries(SCORE_KEYS.map((key) => [key, new Map<number, ZiweiKlineMonth[]>()])) as Record<ZiweiScoreKey, Map<number, ZiweiKlineMonth[]>>
  const volumesByKey = Object.fromEntries(SCORE_KEYS.map((key) => [key, new Map<number, number>()])) as Record<ZiweiScoreKey, Map<number, number>>
  const periodLabels: Array<{ year: number; label: string }> = []

  for (let year = startYear; year <= endYear; year += 1) {
    let yearPeriodLabel = ""
    for (let month = 1; month <= 12; month += 1) {
      const monthHoroscope = safeHoroscope(chart, horoscope, year, month)
      if (!monthHoroscope) continue
      const adjusted = periodAdjustedScores(context, monthHoroscope)
      const overallIntensity = round1(adjusted.impacts.career.intensity * 0.34 + adjusted.impacts.wealth.intensity * 0.26 + adjusted.impacts.relationship.intensity * 0.2 + adjusted.impacts.health.intensity * 0.2)
      const intensityByKey: Record<ZiweiScoreKey, number> = {
        overall: overallIntensity,
        career: adjusted.impacts.career.intensity,
        wealth: adjusted.impacts.wealth.intensity,
        relationship: adjusted.impacts.relationship.intensity,
        health: adjusted.impacts.health.intensity,
      }
      const driversByKey: Record<ZiweiScoreKey, string[]> = {
        overall: [...new Set(SUBJECT_KEYS.flatMap((key) => adjusted.impacts[key].drivers))].slice(0, 5),
        career: adjusted.impacts.career.drivers,
        wealth: adjusted.impacts.wealth.drivers,
        relationship: adjusted.impacts.relationship.drivers,
        health: adjusted.impacts.health.drivers,
      }
      SCORE_KEYS.forEach((key) => {
        const months = monthlyByKey[key].get(year) ?? []
        const previousValue = months[months.length - 1]?.value ?? context.natal_scores[key]
        const value = adjusted.scores[key]
        months.push({
          index: month,
          label: `${year}-${String(month).padStart(2, "0")}`,
          ganzhi: `${String(monthHoroscope.monthly.heavenlyStem)}${String(monthHoroscope.monthly.earthlyBranch)}`,
          value,
          delta: round1(value - previousValue),
          drivers: driversByKey[key],
        })
        monthlyByKey[key].set(year, months)
        volumesByKey[key].set(year, round1((volumesByKey[key].get(year) ?? 0) + intensityByKey[key] * 10))
      })
      if (!yearPeriodLabel) yearPeriodLabel = `${String(monthHoroscope.decadal.heavenlyStem)}${String(monthHoroscope.decadal.earthlyBranch)} · ${String(monthHoroscope.decadal.name)}`
    }
    if (yearPeriodLabel) periodLabels.push({ year, label: yearPeriodLabel })
  }

  const series: ZiweiKlineSeries[] = SCORE_KEYS.map((key) => {
    const points: ZiweiKlinePoint[] = []
    for (let year = startYear; year <= endYear; year += 1) {
      const months = monthlyByKey[key].get(year) ?? []
      if (months.length === 0) continue
      const values = months.map((month) => month.value)
      points.push({
        year,
        open: values[0],
        close: values[values.length - 1],
        high: Math.max(...values),
        low: Math.min(...values),
        volume: volumesByKey[key].get(year) ?? 0,
        ma3: null,
        ma5: null,
        ma10: null,
        months,
      })
    }
    points.forEach((point, index) => {
      point.ma3 = movingAverage(points, index, 3)
      point.ma5 = movingAverage(points, index, 5)
      point.ma10 = movingAverage(points, index, 10)
    })
    return { key, label: labels[key], color: SCORE_COLORS[key], points }
  })
  const stages: ZiweiKlineStage[] = series.flatMap((item) => [...item.points]
    .sort((left, right) => right.close - left.close || left.year - right.year)
    .slice(0, 3)
    .map((point, index) => ({
      key: item.key,
      label: context.locale === "zh" ? `第 ${index + 1} 强阶段` : `Stage ${index + 1}`,
      year: point.year,
      score: point.close,
      theme: item.label,
      summary: context.locale === "zh" ? `${point.year} 年的${item.label}收盘值在当前十年窗口中排名第 ${index + 1}。` : `${point.year} has the #${index + 1} ${item.label.toLowerCase()} close in this ten-year window.`,
    })))
  const result: ZiweiLifeKline = {
    default_window: { start_year: startYear, end_year: endYear },
    series,
    period_bands: mergePeriodBands(periodLabels),
    stages,
    method: "iztro_monthly_midpoint_annual_ohlcv",
  }
  const nextCache = chartCache ?? new Map<string, ZiweiLifeKline>()
  nextCache.set(cacheKey, result)
  if (!chartCache) klineCache.set(chart, nextCache)
  return result
}

export function buildZiweiLifeKline(chart: IFunctionalAstrolabe, horoscope: IFunctionalHoroscope | null | undefined): ZiweiLifeKline {
  return buildZiweiLifeKlineInternal(chart, horoscope)
}

function scoreHeadline(key: ZiweiThemeKey, score: number, locale: ConsumerLocale): string {
  const copy = SUBJECT_COPY[key]
  if (score >= 68) return locale === "zh" ? copy.high_zh : copy.high_en
  if (score >= 48) return locale === "zh" ? copy.mid_zh : copy.mid_en
  return locale === "zh" ? copy.low_zh : copy.low_en
}

function baselineMetadata(statistics: unknown, consumerBaseline: ZiweiConsumerBaseline | null): { id: string | null; hash: string | null } {
  if (consumerBaseline) return { id: consumerBaseline.id, hash: consumerBaseline.hash ?? null }
  const baseline = asRecord(asRecord(statistics)?.baseline)
  return { id: typeof baseline?.id === "string" ? baseline.id : null, hash: typeof baseline?.hash === "string" ? baseline.hash : null }
}

export function buildZiweiConsumerProfile(chart: IFunctionalAstrolabe, horoscope: IFunctionalHoroscope | null | undefined, statistics?: unknown): ZiweiConsumerProfile {
  const context = chartContext(chart)
  const baseline = extractConsumerBaseline(statistics)
  const rarityMetrics = extractRarityMetrics(statistics)
  const globalRanks = Object.fromEntries(SCORE_KEYS.map((key) => [key, rankZiweiGlobalScore(context.natal_scores[key], key, baseline)])) as Record<ZiweiScoreKey, ZiweiRankResult>
  const cohortRanks = Object.fromEntries(SCORE_KEYS.map((key) => [key, rankZiweiCohortScore(context.natal_scores[key], key, context.cohort_id, baseline)])) as Record<ZiweiScoreKey, ZiweiRankResult>
  const archetype = selectArchetype(context)
  const metadata = baselineMetadata(statistics, baseline)
  const subjects = SUBJECT_KEYS.map((key): ZiweiConsumerSubject => ({
    key,
    label: context.locale === "zh" ? SUBJECT_COPY[key].label_zh : SUBJECT_COPY[key].label_en,
    score: Math.round(globalRanks[key].percentile),
    global_percentile: globalRanks[key].percentile,
    global_top_percentage: globalRanks[key].top_percentage,
    cohort_percentile: cohortRanks[key].percentile,
    cohort_top_percentage: cohortRanks[key].top_percentage,
    headline: scoreHeadline(key, globalRanks[key].percentile, context.locale),
  }))
  return {
    version: ZIWEI_CONSUMER_RULES_VERSION,
    system: "ziwei",
    identity: {
      system_title: context.locale === "zh" ? "紫微斗数" : "Zi Wei Dou Shu",
      archetype_title: context.locale === "zh" ? archetype.title : archetype.title_en,
      archetype_subtitle: context.locale === "zh" ? archetype.headline : archetype.headline_en,
      main_score: Math.round(globalRanks.overall.percentile),
      global_percentile: globalRanks.overall.percentile,
      global_top_percentage: globalRanks.overall.top_percentage,
      cohort_percentile: cohortRanks.overall.percentile,
      cohort_top_percentage: cohortRanks.overall.top_percentage,
      cohort_label: context.locale === "zh" ? `同命宫主星组合 · ${context.life_major_ids.map((id) => MAJOR_STAR_LABELS[id].zh).join("×") || "空宫"}` : `Same life-star combination · ${context.life_major_ids.map((id) => MAJOR_STAR_LABELS[id].en).join(" × ") || "Empty"}`,
    },
    subjects,
    achievements: buildAchievements(context, rarityMetrics),
    fingerprints: buildFingerprints(context, horoscope, rarityMetrics),
    twin: buildTwin(context, archetype, baseline, rarityMetrics),
    life_kline: buildZiweiLifeKlineInternal(chart, horoscope, context),
    capability_key: null,
    metadata: {
      rules_version: ZIWEI_CONSUMER_RULES_VERSION,
      archetype_id: archetype.id,
      cohort_id: context.cohort_id,
      baseline_id: metadata.id,
      baseline_hash: metadata.hash,
      rank_sources: {
        global: globalRanks.overall.source,
        cohort: cohortRanks.overall.source,
      },
      raw_scores: Object.fromEntries(SCORE_KEYS.map((key) => [key, round1(context.natal_scores[key])])) as Record<ZiweiScoreKey, number>,
      selected_period: horoscope ? String(horoscope.solarDate) : null,
      scoring_inputs: ["key-palace major stars and brightness", "natal four transformations", "body-palace focus", "six-aid distribution", "six-challenge distribution", "palace trines and opposition"],
      methods: {
        score: "Fixed, versioned additive vectors normalized to 0-100; no AI-generated numbers.",
        rank: baseline ? "Weighted empirical midrank CDF where supplied; deterministic logistic fallback per missing distribution." : "Deterministic logistic fallback; no consumer histogram was supplied.",
        kline: "Annual OHLC candles from twelve iztro monthly midpoint states per year across the default ten-year window; volume is weighted activation intensity.",
      },
      sources: ["iztro 2.5.8 functional astrolabe and horoscope fields", metadata.id ? `baseline:${metadata.id}` : "built-in deterministic fallback"],
    },
  }
}
