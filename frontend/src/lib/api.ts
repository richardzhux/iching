import type {
  ChatTranscriptResponse,
  ChatMessage,
  ChatTurnPayload,
  ChatTurnResponse,
  ConfigResponse,
  MetaphysicsChart,
  MetaphysicsChartListResponse,
  MetaphysicsChartRecord,
  MetaphysicsChartRequest,
  DayunCycle,
  MetaphysicsChartSavePayload,
  MetaphysicsStatistics,
  PatternRuleSummary,
  SessionHistoryResponse,
  SessionPayload,
  SessionRequest,
} from "@/types/api"
import { getApiBaseUrl } from "@/lib/env"

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
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/config`, {
    cache: "no-store",
  })
  return handleResponse<ConfigResponse>(response)
}

export async function calculateMetaphysicsChart(payload: MetaphysicsChartRequest): Promise<MetaphysicsChart> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/tools/metaphysics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  return handleResponse<MetaphysicsChart>(response)
}

export async function fetchMetaphysicsPeriod(payload: MetaphysicsChartRequest & { cycle_index: number }): Promise<DayunCycle> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/tools/metaphysics/periods`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  const result = await handleResponse<{ cycle: DayunCycle }>(response)
  return result.cycle
}

export async function fetchMetaphysicsStatistics(payload: { chart_type: "bazi" | "ziwei"; baseline_id: string; feature_ids: string[] }): Promise<MetaphysicsStatistics> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/tools/metaphysics/statistics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  return handleResponse<MetaphysicsStatistics>(response)
}

export async function fetchPatternRuleSummary(bundleId: string, ruleId: string): Promise<PatternRuleSummary> {
  const response = await fetchWithTimeout(
    `${getApiBaseUrl()}/api/tools/metaphysics/pattern-rules/${encodeURIComponent(bundleId)}/${encodeURIComponent(ruleId)}`,
    { cache: "no-store" },
  )
  return handleResponse<PatternRuleSummary>(response)
}

export async function saveMetaphysicsChart(payload: MetaphysicsChartSavePayload, token: string): Promise<MetaphysicsChartRecord> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/metaphysics/charts`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  })
  return handleResponse<MetaphysicsChartRecord>(response)
}

export async function fetchMetaphysicsChart(chartId: string, token: string): Promise<MetaphysicsChartRecord> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/metaphysics/charts/${chartId}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  })
  return handleResponse<MetaphysicsChartRecord>(response)
}

export async function fetchMetaphysicsCharts(token: string): Promise<MetaphysicsChartListResponse> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/metaphysics/charts`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  })
  return handleResponse<MetaphysicsChartListResponse>(response)
}

export async function deleteMetaphysicsChart(chartId: string, token: string): Promise<void> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/metaphysics/charts/${chartId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new Error(await response.text())
}

export async function createSession(request: SessionRequest, token?: string): Promise<SessionPayload> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/sessions`, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  })
  return handleResponse<SessionPayload>(response)
}

export async function fetchChatTranscript(sessionId: string, token: string): Promise<ChatTranscriptResponse> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/sessions/${sessionId}/chat`, {
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
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/sessions/${sessionId}/chat`, {
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
      restart: payload.restart ?? undefined,
    }),
  })
  return handleResponse<ChatTurnResponse>(response)
}

export async function streamChatMessage(
  sessionId: string,
  token: string,
  payload: ChatTurnPayload,
  options: {
    signal?: AbortSignal
    onDelta: (delta: string) => void
  },
): Promise<ChatTurnResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/sessions/${sessionId}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      message: payload.message,
      reasoning: payload.reasoning ?? undefined,
      verbosity: payload.verbosity ?? undefined,
      tone: payload.tone ?? undefined,
      model: payload.model ?? undefined,
      restart: payload.restart ?? undefined,
    }),
    signal: options.signal,
  })
  if (!response.ok) {
    return handleResponse<ChatTurnResponse>(response)
  }
  if (!response.body) {
    throw new Error("Streaming response body is unavailable.")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let completed: ChatTurnResponse | null = null

  const consumeBlock = (block: string) => {
    let eventType = "message"
    const dataLines: string[] = []
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) eventType = line.slice(6).trim()
      if (line.startsWith("data:")) dataLines.push(line.slice(5).trim())
    }
    if (!dataLines.length) return
    const data = JSON.parse(dataLines.join("\n")) as Record<string, unknown>
    if (eventType === "delta") {
      options.onDelta(String(data.delta ?? ""))
    } else if (eventType === "completed") {
      completed = {
        session_id: sessionId,
        assistant: data.assistant as ChatMessage,
        usage: (data.usage as Record<string, number>) ?? {},
      }
    } else if (eventType === "error") {
      throw new Error(String(data.detail ?? "AI stream failed."))
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    let boundary = buffer.indexOf("\n\n")
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary).trim()
      buffer = buffer.slice(boundary + 2)
      if (block) consumeBlock(block)
      boundary = buffer.indexOf("\n\n")
    }
    if (done) break
  }
  if (buffer.trim()) consumeBlock(buffer.trim())
  if (!completed) {
    throw new Error("AI stream ended before completion.")
  }
  return completed
}

export async function fetchSessionHistory(token: string): Promise<SessionHistoryResponse> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/sessions`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  })
  return handleResponse<SessionHistoryResponse>(response)
}

export async function deleteSession(sessionId: string, token: string): Promise<void> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/sessions/${sessionId}`, {
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
