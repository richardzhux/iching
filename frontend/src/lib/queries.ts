import { useMutation, useQuery } from "@tanstack/react-query"
import { createSession, fetchConfig, fetchSessionHistory } from "@/lib/api"
import type { SessionPayload, SessionRequest } from "@/types/api"

export function useConfigQuery() {
  return useQuery({
    queryKey: ["config"],
    queryFn: fetchConfig,
  })
}

type SessionMutationOptions = {
  onSuccess?: (payload: SessionPayload) => void
  onError?: (error: Error) => void
  accessToken?: string
}

export function useSessionMutation(options?: SessionMutationOptions) {
  return useMutation({
    mutationFn: (payload: SessionRequest) => createSession(payload, options?.accessToken ?? undefined),
    onSuccess: options?.onSuccess,
    onError: options?.onError,
  })
}

export function useSessionHistoryQuery(accessToken: string | null) {
  return useQuery({
    queryKey: ["session-history", accessToken],
    queryFn: () => {
      if (!accessToken) {
        throw new Error("Authentication required to read session history.")
      }
      return fetchSessionHistory(accessToken)
    },
    enabled: Boolean(accessToken),
  })
}
