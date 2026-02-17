"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"

export function HomePage() {
  const { locale, messages, toLocalePath } = useI18n()

  if (locale === "zh" || locale === "en") {
    const copy =
      locale === "zh"
        ? {
            badge: "I Ching Studio · FastAPI + Next.js",
            title: "🔮从蓍草到AI：开启专属于你的易经旅程",
            subtitle: "让千年易学典籍与现代 AI 推演温柔相遇。",
            primaryCta: "进入工作台",
            secondaryCta: "查看开发文档",
            features: [
              "手动 / 随机起卦与时间控制",
              "AI 推理力度与篇幅调节",
              "自动归档 + 会话历史",
            ],
            upcomingLabel: "即将推出",
            upcomingBody: (
              <>
                全新深度融合AI对话功能，实时调取解读易学经典。
                <br />
                自定义深度学术研究组件。
              </>
            ),
            workbenchTitle: "AI WORKBENCH",
            workbenchBody:
              "厌倦了 ChatGPT 式含糊其辞、过度迎合甚至幻觉？我们的对话直接连上后端 Python 推演引擎与占卜档案，按问题与卦象逐条给出可验证的判断，还能在五款模型之间切换，调节篇幅与思考深度。",
            researchTitle: "DEEP ARCHIVAL RESEARCH",
            researchBody:
              "原文级易学经典库全量内置，可按朝代、学派自定义引用，阅读真实文本而非模糊 AI 摘要，形成独一无二的学术工作流。",
          }
        : {
            badge: "I Ching Studio · FastAPI + Next.js",
            title: "🔮From yarrow stalks to AI: begin your personal I Ching journey",
            subtitle: "Let millennia of Yijing classics meet modern AI reasoning, gently.",
            primaryCta: "Enter Workspace",
            secondaryCta: "View Developer Docs",
            features: [
              "Manual / random hexagram casting with time control",
              "AI reasoning-intensity and response-length tuning",
              "Auto archiving + session history",
            ],
            upcomingLabel: "Coming Soon",
            upcomingBody: (
              <>
                A brand-new deeply integrated AI dialogue feature, drawing from I Ching classics in real time.
                <br />
                Custom deep academic research modules.
              </>
            ),
            workbenchTitle: "AI WORKBENCH",
            workbenchBody:
              "Tired of ChatGPT-style vagueness, over-accommodation, or hallucinations? Our dialogue connects directly to the backend Python inference engine and divination archive, delivering verifiable, line-by-line judgments from your question and hexagram. You can also switch among five models and tune response length and thinking depth.",
            researchTitle: "DEEP ARCHIVAL RESEARCH",
            researchBody:
              "A full source-level corpus of I Ching classics is built in. Cite by dynasty and school, read original texts instead of fuzzy AI summaries, and shape a one-of-a-kind scholarly workflow.",
          }

    return (
      <main className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-14 px-6 py-20 lg:flex-row lg:items-center lg:gap-24 lg:px-12">
        <section className="space-y-8 text-center lg:w-[52%] lg:text-left">
          <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-background/70 px-4 py-1 text-sm text-muted-foreground shadow-glass backdrop-blur dark:border-white/20 dark:bg-white/10 dark:text-white/80">
            <span className="size-2 rounded-full bg-primary/80" />
            {copy.badge}
          </div>
          <div className="space-y-6">
            <h1 className="text-4xl font-semibold leading-relaxed tracking-tight text-foreground md:text-5xl">
              {copy.title}
            </h1>
            <p className="text-lg text-muted-foreground md:text-xl">{copy.subtitle}</p>
          </div>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <Button asChild size="lg" className="rounded-full px-8 text-base font-semibold">
              <Link href={toLocalePath("/app")}>{copy.primaryCta}</Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="rounded-full px-8 text-base text-foreground hover:bg-foreground/10 dark:text-white"
            >
              <a href="https://github.com/richardzhux/iching" target="_blank" rel="noreferrer">
                {copy.secondaryCta}
              </a>
            </Button>
          </div>
          <ul className="space-y-2 text-left text-muted-foreground">
            {copy.features.map((item) => (
              <li key={item} className="flex items-center gap-2">
                <span className="size-1.5 rounded-full bg-primary/80" />
                {item}
              </li>
            ))}
          </ul>
        </section>

        <section className="glass-panel relative flex w-full flex-col gap-6 rounded-3xl p-8 text-left text-foreground shadow-glass backdrop-blur lg:w-[48%]">
          <div className="panel-heading">{copy.upcomingLabel}</div>
          <p className="text-2xl font-semibold leading-snug">{copy.upcomingBody}</p>
          <div className="space-y-4 text-sm text-muted-foreground">
            <div className="rounded-2xl border border-border/50 bg-foreground/[0.04] p-4 dark:border-white/15 dark:bg-white/5">
              <div className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">{copy.workbenchTitle}</div>
              <p className="mt-2 text-base text-foreground">{copy.workbenchBody}</p>
            </div>
            <div className="rounded-2xl border border-border/50 bg-foreground/[0.04] p-4 dark:border-white/15 dark:bg-white/5">
              <div className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">{copy.researchTitle}</div>
              <p className="mt-2 text-base text-foreground">{copy.researchBody}</p>
            </div>
          </div>
        </section>
      </main>
    )
  }

  return (
    <main className="grid min-h-[calc(100vh-8rem)] items-center gap-10 py-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14">
      <section className="space-y-7">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-surface/70 px-4 py-1 text-xs font-medium text-muted-foreground backdrop-blur"
        >
          <span className="size-2 rounded-full bg-primary/80" />
          {messages.home.badge}
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05, duration: 0.35 }}
          className="space-y-4"
        >
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            {messages.home.title}
          </h1>
          <p className="max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            {messages.home.subtitle}
          </p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.35 }}
          className="flex flex-wrap items-center gap-3"
        >
          <Button asChild size="lg" className="rounded-full px-7 text-sm font-semibold">
            <Link href={toLocalePath("/app")}>{messages.home.primaryCta}</Link>
          </Button>
          <Button
            asChild
            size="lg"
            variant="outline"
            className="rounded-full px-7 text-sm font-semibold"
          >
            <a href="https://github.com/richardzhux/iching" target="_blank" rel="noreferrer">
              {messages.home.secondaryCta}
            </a>
          </Button>
        </motion.div>
        <motion.ul
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.35 }}
          className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-2"
        >
          {messages.home.features.map((feature) => (
            <li key={feature} className="flex items-start gap-2">
              <span className="mt-1.5 size-1.5 rounded-full bg-primary/80" />
              <span>{feature}</span>
            </li>
          ))}
        </motion.ul>
      </section>

      <section className="space-y-4">
        <motion.article
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08, duration: 0.4 }}
          className="surface-card space-y-3 rounded-3xl p-6"
        >
          <p className="kicker">{messages.home.studioLabel}</p>
          <h2 className="text-xl font-semibold text-foreground">{messages.home.studioTitle}</h2>
          <p className="text-sm leading-relaxed text-muted-foreground">{messages.home.studioBody}</p>
        </motion.article>
        <motion.article
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.4 }}
          className="surface-card space-y-3 rounded-3xl p-6"
        >
          <p className="kicker">{messages.home.researchLabel}</p>
          <p className="text-sm leading-relaxed text-muted-foreground">{messages.home.researchBody}</p>
        </motion.article>
      </section>
    </main>
  )
}
