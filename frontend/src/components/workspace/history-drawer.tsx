"use client"

import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { useWorkspaceStore } from "@/lib/store"

export function HistoryDrawer() {
  const { history } = useWorkspaceStore((state) => ({
    history: state.history,
  }))

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" className="w-full rounded-full border-white/30 bg-white/10 text-white hover:bg-white/20">
          查看会话历史 ({history.length})
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>最近 10 次起卦</SheetTitle>
          <SheetDescription>仅保留当前浏览器内存，刷新后将清空。</SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-5">
          {history.length === 0 && <p className="text-sm text-muted-foreground">暂无历史记录。</p>}
          {history.map((item, index) => (
            <div
              key={`${item.archive_path}-${index}`}
              className="rounded-2xl border border-border/70 bg-card/70 p-4 text-sm shadow-glass"
            >
              <p className="text-xs uppercase tracking-[0.3rem] text-muted-foreground">
                {item.session_dict?.method as string}
              </p>
              <p className="mt-1 font-semibold">{item.session_dict?.topic as string}</p>
              <p className="text-xs text-muted-foreground">
                {item.session_dict?.current_time_str as string} · {item.archive_path.split("/").pop()}
              </p>
              <pre className="mt-2 whitespace-pre-wrap text-xs text-muted-foreground">
                {(item.session_dict?.user_question as string) || "（未填写问题）"}
              </pre>
            </div>
          ))}
        </div>
      </SheetContent>
    </Sheet>
  )
}
