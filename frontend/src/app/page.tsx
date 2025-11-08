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
      <section className="space-y-8 text-center lg:text-left">
        <div className="inline-flex items-center gap-2 rounded-full border border-white/25 px-4 py-1 text-sm text-white/80 shadow-glass backdrop-blur">
          <span className="size-2 rounded-full bg-primary" />
          I Ching Studio · FastAPI + Next.js
        </div>
        <div className="space-y-6">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight text-white md:text-5xl">
            精准的《易经》占卜体验 <br className="hidden md:block" />
            现代界面 · API 驱动
          </h1>
          <p className="text-lg text-white/80 md:text-xl">
            FastAPI 承载核心算法，Next.js + shadcn/ui 提供全新的工作台。即将上线的 React
            前端可自定义主题、面板与快捷操作，让易经知识与 AI 解读无缝衔接。
          </p>
        </div>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <Button asChild size="lg" className="rounded-full px-8 text-base font-semibold">
            <Link href="/app">进入工作台</Link>
          </Button>
          <Button
            asChild
            size="lg"
            variant="outline"
            className="rounded-full border-white/40 bg-white/5 px-8 text-base text-white hover:bg-white/10"
          >
            <a href="https://github.com" target="_blank" rel="noreferrer">
              查看后端 API
            </a>
          </Button>
        </div>
        <ul className="space-y-2 text-left text-white/75">
          {features.map((item) => (
            <li key={item} className="flex items-center gap-2">
              <span className="size-1.5 rounded-full bg-white" />
              {item}
            </li>
          ))}
        </ul>
      </section>

      <section className="glass-panel relative flex w-full flex-col gap-6 rounded-3xl p-8 text-left text-white shadow-glass backdrop-blur">
        <div className="panel-heading">即将推出</div>
        <p className="text-2xl font-semibold leading-snug">
          新的 React 界面以组件化方式呈现，会话历史、AI 控制、结果导出都可以自定义扩展。
        </p>
        <div className="space-y-4 text-sm text-white/80">
          <div className="rounded-2xl border border-white/15 bg-black/30 p-4">
            <div className="text-xs uppercase tracking-[0.35rem] text-white/60">Backend</div>
            <p className="mt-2 text-base text-white">
              FastAPI 部署在 Render，公开 `/api/config` 与 `/api/sessions` 端点。
            </p>
          </div>
          <div className="rounded-2xl border border-white/15 bg-black/30 p-4">
            <div className="text-xs uppercase tracking-[0.35rem] text-white/60">Frontend</div>
            <p className="mt-2 text-base text-white">
              Next.js App Router + Tailwind + shadcn，提供玻璃拟态工作流与暗色主题。
            </p>
          </div>
        </div>
      </section>
    </main>
  )
}
