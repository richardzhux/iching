import type { Locale } from "@/i18n/config"

type TopicOption = {
  label: string
}

export const READING_INTENTS = {
  career: {
    topic: "事业",
    questionHint: {
      en: "What should I understand about my career direction, timing, and next action?",
      zh: "我应该怎样理解事业方向、时机与下一步行动？",
    },
  },
  relationship: {
    topic: "感情",
    questionHint: {
      en: "What should I understand about this relationship, its timing, and how to respond?",
      zh: "我应该怎样理解这段关系、当前时机与回应方式？",
    },
  },
  choice: {
    topic: "其他/跳过",
    questionHint: {
      en: "What should I understand about this choice, its trade-offs, and the right timing?",
      zh: "我应该怎样理解这个选择的取舍、后果与合适时机？",
    },
  },
  current: {
    topic: "整体运势",
    questionHint: {
      en: "What should I understand about my present situation and the next useful action?",
      zh: "我应该怎样理解当下的整体局势与下一步行动？",
    },
  },
} as const

export type ReadingIntentId = keyof typeof READING_INTENTS

export function resolveReadingIntent(
  intentId: string | null,
  locale: Locale,
  availableTopics: readonly TopicOption[],
) {
  if (!intentId || !(intentId in READING_INTENTS)) return null

  const id = intentId as ReadingIntentId
  const intent = READING_INTENTS[id]
  if (!availableTopics.some((topic) => topic.label === intent.topic)) return null

  return {
    id,
    topic: intent.topic,
    questionHint: intent.questionHint[locale],
  }
}
