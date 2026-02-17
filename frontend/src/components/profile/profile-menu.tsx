"use client"

import Link from "next/link"
import { Loader2, UserRound } from "lucide-react"
import { useState } from "react"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { useAuthContext } from "@/components/providers/auth-provider"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

export function ProfileMenu() {
  const auth = useAuthContext()
  const { messages, toLocalePath } = useI18n()
  const [open, setOpen] = useState(false)
  const initials = (auth.displayName?.[0] || auth.user?.email?.[0] || "G").toUpperCase()
  const label = auth.displayName ?? auth.user?.email ?? "Guest"

  async function handleSignOut() {
    try {
      await auth.signOut()
      toast.success(messages.profileMenu.signedOutToast)
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
          aria-label={messages.profileMenu.ariaOpen}
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
            {messages.profileMenu.checkingAuth}
          </div>
        ) : auth.user ? (
          <>
            <div>
              <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">{messages.profileMenu.signedIn}</p>
              <p className="text-base font-semibold text-foreground">{label}</p>
              <p className="text-xs text-muted-foreground">{auth.user?.email}</p>
            </div>
            <div className="flex flex-col gap-2">
              <Button asChild variant="outline">
                <Link href={toLocalePath("/profile")} onClick={() => setOpen(false)}>
                  {messages.profileMenu.openProfile}
                </Link>
              </Button>
              <Button variant="ghost" onClick={handleSignOut}>
                {messages.common.signOut}
              </Button>
            </div>
          </>
        ) : (
          <>
            <div>
              <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">{messages.profileMenu.guestMode}</p>
              <p className="text-sm text-muted-foreground">
                {messages.profileMenu.guestHint}
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <Button asChild>
                <Link href={toLocalePath("/profile")} onClick={() => setOpen(false)}>
                  {messages.profileMenu.signInRegister}
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href={toLocalePath("/app")}>{messages.profileMenu.goWorkspace}</Link>
              </Button>
            </div>
          </>
        )}
      </PopoverContent>
    </Popover>
  )
}
