"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { type ReactNode, useState } from "react"

type Props = {
  children: ReactNode
}

export function QueryProvider({ children }: Props) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            staleTime: 5 * 60 * 1000,
            retry: (failureCount, error) => {
              if (failureCount >= 2) return false
              const message = (error as Error)?.message || ""
              if (message.includes("401") || message.includes("403")) {
                return false
              }
              return true
            },
            retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 4000),
          },
        },
      }),
  )

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
