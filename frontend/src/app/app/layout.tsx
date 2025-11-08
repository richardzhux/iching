import type { Metadata } from "next"
import Link from "next/link"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export const metadata: Metadata = {
  title: "I Ching Studio · 工作台",
  description: "沉浸式玻璃拟态工作台，连通 FastAPI 后端",
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-12 lg:px-12">
      <header className="mb-10 flex flex-col gap-4 rounded-3xl border border-white/15 bg-white/5 p-6 text-white shadow-glass backdrop-blur lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="panel-heading">I Ching Studio</p>
          <h1 className="text-2xl font-semibold">占卜工作台</h1>
          <p className="text-sm text-white/80">
            Next.js 前端消费 FastAPI API · 支持 AI 分析、自动归档与玻璃拟态主题。
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link href="/" className={cn(buttonVariants({ variant: "outline" }), "rounded-full")}>
            返回主站
          </Link>
          <a
            href="https://docs.google.com"
            target="_blank"
            rel="noreferrer"
            className={cn(buttonVariants({ variant: "default" }), "rounded-full bg-white text-primary")}
          >
            开发文档
          </a>
        </div>
      </header>
      {children}
    </div>
  )
}
