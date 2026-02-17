import type {
  ChatTranscriptResponse,
  ChatTurnPayload,
  ChatTurnResponse,
  ConfigResponse,
  SessionHistoryResponse,
  SessionPayload,
  SessionRequest,
} from "@/types/api"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
const DEFAULT_TIMEOUT_MS = 30000

type RequestOptions = RequestInit & { timeoutMs?: number }

async function fetchWithTimeout(input: string, options: RequestOptions = {}): Promise<Response> {
  const controller = new AbortController()
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const timeoutId = setTimeout(() => {
    controller.abort()
  }, timeoutMs)

  try {
    return await fetch(input, {
      ...options,
      signal: controller.signal,
    })
  } catch (error) {
    if ((error as Error).name === "AbortError") {
      throw new Error("Request timed out. Please try again.")
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = "Request failed. Please try again."
    try {
      const data = await response.json()
      if (typeof data === "string") {
        message = data
      } else if (data?.detail) {
        if (typeof data.detail === "string") {
          message = data.detail
        } else if (Array.isArray(data.detail)) {
          message = data.detail
            .map((item: { msg?: string; detail?: string }) => item?.msg || item?.detail)
            .filter(Boolean)
            .join("；")
        }
      }
    } catch {
      try {
        message = await response.text()
      } catch {
        // ignore
      }
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export async function fetchConfig(): Promise<ConfigResponse> {
  const response = await fetchWithTimeout(`${API_BASE}/api/config`, {
    cache: "no-store",
  })
  return handleResponse<ConfigResponse>(response)
}

export async function createSession(request: SessionRequest, token?: string): Promise<SessionPayload> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  const response = await fetchWithTimeout(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  })
  return handleResponse<SessionPayload>(response)
}

export async function fetchChatTranscript(sessionId: string, token: string): Promise<ChatTranscriptResponse> {
  const response = await fetchWithTimeout(`${API_BASE}/api/sessions/${sessionId}/chat`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  })
  return handleResponse<ChatTranscriptResponse>(response)
}

export async function sendChatMessage(
  sessionId: string,
  token: string,
  payload: ChatTurnPayload,
): Promise<ChatTurnResponse> {
  const response = await fetchWithTimeout(`${API_BASE}/api/sessions/${sessionId}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      message: payload.message,
      reasoning: payload.reasoning ?? undefined,
      verbosity: payload.verbosity ?? undefined,
      tone: payload.tone ?? undefined,
      model: payload.model ?? undefined,
    }),
  })
  return handleResponse<ChatTurnResponse>(response)
}

export async function fetchSessionHistory(token: string): Promise<SessionHistoryResponse> {
  const response = await fetchWithTimeout(`${API_BASE}/api/sessions`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  })
  return handleResponse<SessionHistoryResponse>(response)
}

export async function deleteSession(sessionId: string, token: string): Promise<void> {
  const response = await fetchWithTimeout(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  if (!response.ok) {
    throw new Error(await response.text())
  }
}

export function parseManualLines(input: string): number[] | undefined {
  const trimmed = input.trim()
  if (!trimmed) return undefined

  if (/^[6789]{6}$/.test(trimmed)) {
    return trimmed.split("").map((digit) => Number(digit))
  }

  const tokens = trimmed
    .replace(/，/g, ",")
    .split(",")
    .map((token) => token.trim())
    .filter(Boolean)

  if (tokens.length !== 6) {
    throw new Error("manual_lines_count_error")
  }

  const values = tokens.map((token) => {
    const value = Number(token)
    if (![6, 7, 8, 9].includes(value)) {
      throw new Error("manual_lines_value_error")
    }
    return value
  })

  return values
}
