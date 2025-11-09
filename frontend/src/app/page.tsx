import Link from "next/link"
import { Button } from "@/components/ui/button"

const features = [
  "手动 / 随机起卦与时间控制",
  "AI 推理力度与篇幅调节",
  "自动归档 + 会话历史",
]

export default function Home() {
  return (
    <main className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-14 px-6 py-20 lg:flex-row lg:items-center lg:gap-24 lg:px-12">
      <section className="space-y-8 text-center lg:w-[52%] lg:text-left">
        <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-background/70 px-4 py-1 text-sm text-muted-foreground shadow-glass backdrop-blur dark:border-white/20 dark:bg-white/10 dark:text-white/80">
          <span className="size-2 rounded-full bg-primary/80" />
          I Ching Studio · FastAPI + Next.js
        </div>
        <div className="space-y-6">
          <h1 className="text-4xl font-semibold leading-relaxed tracking-tight text-foreground md:text-5xl">
            🔮从蓍草到AI：开启专属于你的易经旅程
          </h1>
          <p className="text-lg text-muted-foreground md:text-xl">让千年易学典籍与现代 AI 推演温柔相遇。</p>
        </div>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <Button asChild size="lg" className="rounded-full px-8 text-base font-semibold">
            <Link href="/app">进入工作台</Link>
          </Button>
          <Button
            asChild
            size="lg"
            variant="outline"
            className="rounded-full px-8 text-base text-foreground hover:bg-foreground/10 dark:text-white"
          >
            <a href="https://github.com/richardzhux/iching" target="_blank" rel="noreferrer">
              查看开发文档
            </a>
          </Button>
        </div>
        <ul className="space-y-2 text-left text-muted-foreground">
          {features.map((item) => (
            <li key={item} className="flex items-center gap-2">
              <span className="size-1.5 rounded-full bg-primary/80" />
              {item}
            </li>
          ))}
        </ul>
      </section>

      <section className="glass-panel relative flex w-full flex-col gap-6 rounded-3xl p-8 text-left text-foreground shadow-glass backdrop-blur lg:w-[48%]">
        <div className="panel-heading">即将推出</div>
        <p className="text-2xl font-semibold leading-snug">
          全新深度融合AI对话功能，实时调取解读易学经典。
          <br />
          自定义深度学术研究组件。
        </p>
        <div className="space-y-4 text-sm text-muted-foreground">
          <div className="rounded-2xl border border-border/50 bg-foreground/[0.04] p-4 dark:border-white/15 dark:bg-white/5">
            <div className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">AI WORKBENCH</div>
            <p className="mt-2 text-base text-foreground">
              厌倦了 ChatGPT 式含糊其辞、过度迎合甚至幻觉？我们的对话直接连上后端 Python 推演引擎与占卜档案，按问题与卦象逐条给出可验证的判断，还能在五款模型之间切换，调节篇幅与思考深度。
            </p>
          </div>
          <div className="rounded-2xl border border-border/50 bg-foreground/[0.04] p-4 dark:border-white/15 dark:bg-white/5">
            <div className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">DEEP ARCHIVAL RESEARCH</div>
            <p className="mt-2 text-base text-foreground">
              原文级易学经典库全量内置，可按朝代、学派自定义引用，阅读真实文本而非模糊 AI 摘要，形成独一无二的学术工作流。
            </p>
          </div>
        </div>
      </section>
    </main>
  )
}
