import { useMutation, useQuery } from "@tanstack/react-query"
import { createSession, fetchConfig } from "@/lib/api"
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
}

export function useSessionMutation(options?: SessionMutationOptions) {
  return useMutation({
    mutationFn: (payload: SessionRequest) => createSession(payload),
    onSuccess: options?.onSuccess,
    onError: options?.onError,
  })
}
