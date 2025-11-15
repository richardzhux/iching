"use client"

import Link from "next/link"
import { Loader2, UserRound } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { useAuthContext } from "@/components/providers/auth-provider"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

export function ProfileMenu() {
  const auth = useAuthContext()
  const [open, setOpen] = useState(false)
  const initials = (auth.displayName?.[0] || auth.user?.email?.[0] || "访").toUpperCase()
  const label = auth.displayName ?? auth.user?.email ?? "游客"

  async function handleSignOut() {
    try {
      await auth.signOut()
      toast.success("已退出登录。")
      setOpen(false)
    } catch (error) {
      toast.error((error as Error).message)
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "flex size-10 items-center justify-center rounded-full border border-border/40 bg-background/70 text-sm font-semibold text-foreground shadow-glass transition hover:border-foreground/70 dark:border-white/30 dark:bg-white/10 dark:text-white",
            auth.user ? "uppercase" : "",
          )}
          aria-label="打开个人中心"
        >
          {auth.loading ? (
            <Loader2 className="size-4 animate-spin" />
          ) : auth.avatarUrl ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={auth.avatarUrl} alt={label} className="size-8 rounded-full object-cover" />
            </>
          ) : auth.user ? (
            initials
          ) : (
            <UserRound className="size-4" />
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-72 space-y-4 text-sm">
        {auth.loading ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            正在检测登录状态…
          </div>
        ) : auth.user ? (
          <>
            <div>
              <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">已登录</p>
              <p className="text-base font-semibold text-foreground">{label}</p>
              <p className="text-xs text-muted-foreground">{auth.user?.email}</p>
            </div>
            <div className="flex flex-col gap-2">
              <Button asChild variant="outline">
                <Link href="/profile" onClick={() => setOpen(false)}>
                  进入个人中心
                </Link>
              </Button>
              <Button variant="ghost" onClick={handleSignOut}>
                退出登录
              </Button>
            </div>
          </>
        ) : (
          <>
            <div>
              <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">游客模式</p>
              <p className="text-sm text-muted-foreground">
                登录后即可启用 AI、查看完整占卜历史，并安全备份到 Supabase。
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <Button asChild>
                <Link href="/profile" onClick={() => setOpen(false)}>
                  登录 / 注册
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/app">返回工作台</Link>
              </Button>
            </div>
          </>
        )}
      </PopoverContent>
    </Popover>
  )
}
