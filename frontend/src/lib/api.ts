import type {
  CastingPreview,
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
  PatternLibrary,
  PatternRuleSummary,
  SessionHistoryResponse,
  SessionPayload,
  SessionRequest,
} from "@/types/api"
import { getApiBaseUrl } from "@/lib/env"

const DEFAULT_TIMEOUT_MS = 30000
const AI_TIMEOUT_MS = 180000
const STREAM_STALL_TIMEOUT_MS = 120000
const SNAPSHOT_COMPRESSION_THRESHOLD_BYTES = 256 * 1024

type RequestOptions = RequestInit & { timeoutMs?: number }

async function fetchWithTimeout(input: string, options: RequestOptions = {}): Promise<Response> {
  const { signal, timeoutMs = DEFAULT_TIMEOUT_MS, ...requestOptions } = options
  const controller = new AbortController()
  const requestSignal = signal ? AbortSignal.any([signal, controller.signal]) : controller.signal
  let timedOut = false
  const timeoutId = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)

  try {
    return await fetch(input, {
      ...requestOptions,
      signal: requestSignal,
    })
  } catch (error) {
    if (timedOut && !signal?.aborted) {
      throw new Error("Request timed out. It may still be running; retry the same request.")
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = response.status === 409
      ? "The request may still be running; retry the same request."
      : "Request failed. Please try again."
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

export async function prepareCasting(methodKey: "s" | "m", timestamp: string, meihuaMode = "traditional", timezone?: string): Promise<CastingPreview> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/casting/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ method_key: methodKey, timestamp, meihua_mode: meihuaMode, timezone }),
  })
  return handleResponse<CastingPreview>(response)
}

export async function calculateMetaphysicsChart(payload: MetaphysicsChartRequest): Promise<MetaphysicsChart> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/tools/metaphysics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  return handleResponse<MetaphysicsChart>(response)
}

export async function fetchMetaphysicsPeriod(payload: MetaphysicsChartRequest & { cycle_index: number }, options: { signal?: AbortSignal } = {}): Promise<DayunCycle> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/tools/metaphysics/periods`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: options.signal,
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

export async function fetchPatternLibrary(patternId: string): Promise<PatternLibrary> {
  const response = await fetchWithTimeout(
    `${getApiBaseUrl()}/api/tools/metaphysics/pattern-library/${encodeURIComponent(patternId)}`,
    { cache: "force-cache" },
  )
  return handleResponse<PatternLibrary>(response)
}

export async function saveMetaphysicsChart(payload: MetaphysicsChartSavePayload, token: string): Promise<MetaphysicsChartRecord> {
  const snapshotBytes = new TextEncoder().encode(JSON.stringify(payload.result_snapshot))
  let snapshot = payload.result_snapshot
  if (snapshotBytes.byteLength > SNAPSHOT_COMPRESSION_THRESHOLD_BYTES) {
    if (typeof CompressionStream === "undefined") {
      throw new Error("This browser cannot save a large chart. Update your browser and try again; the chart remains open.")
    }
    const compressedStream = new Blob([snapshotBytes]).stream().pipeThrough(new CompressionStream("gzip"))
    const compressedBytes = new Uint8Array(await new Response(compressedStream).arrayBuffer())
    let binary = ""
    // Limit spread arguments so large snapshots cannot exhaust the JS stack.
    for (let offset = 0; offset < compressedBytes.length; offset += 0x8000) {
      binary += String.fromCharCode(...compressedBytes.subarray(offset, offset + 0x8000))
    }
    snapshot = { _encoding: "iching.chart-snapshot.gzip.v1", data: btoa(binary) }
  }
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/metaphysics/charts`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ ...payload, result_snapshot: snapshot }),
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
    timeoutMs: request.enable_ai ? AI_TIMEOUT_MS : DEFAULT_TIMEOUT_MS,
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
    timeoutMs: AI_TIMEOUT_MS,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      request_id: payload.request_id,
      access_password: payload.access_password,
      message: payload.message,
      reasoning: payload.reasoning ?? undefined,
      verbosity: payload.verbosity ?? undefined,
      tone: payload.tone ?? undefined,
      model: payload.model ?? undefined,
      restart: payload.restart ?? undefined,
      locale: payload.locale ?? undefined,
    }),
  })
  return handleResponse<ChatTurnResponse>(response)
}

export async function fetchSession(sessionId: string, token: string): Promise<SessionPayload> {
  const response = await fetchWithTimeout(`${getApiBaseUrl()}/api/sessions/${sessionId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return handleResponse<SessionPayload>(response)
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
  const controller = new AbortController()
  const signal = options.signal ? AbortSignal.any([options.signal, controller.signal]) : controller.signal
  let timeoutReason: "total" | "stall" | null = null
  const totalTimeoutId = setTimeout(() => {
    timeoutReason = "total"
    controller.abort()
  }, AI_TIMEOUT_MS)
  let stallTimeoutId: ReturnType<typeof setTimeout> | undefined
  const resetStallTimeout = () => {
    clearTimeout(stallTimeoutId)
    stallTimeoutId = setTimeout(() => {
      timeoutReason = "stall"
      controller.abort()
    }, STREAM_STALL_TIMEOUT_MS)
  }
  resetStallTimeout()
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined

  try {
    const response = await fetch(`${getApiBaseUrl()}/api/sessions/${sessionId}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        Accept: "text/event-stream",
      },
      body: JSON.stringify({
        request_id: payload.request_id,
        access_password: payload.access_password,
        message: payload.message,
        reasoning: payload.reasoning ?? undefined,
        verbosity: payload.verbosity ?? undefined,
        tone: payload.tone ?? undefined,
        model: payload.model ?? undefined,
        restart: payload.restart ?? undefined,
        locale: payload.locale ?? undefined,
      }),
      signal,
    })
    if (!response.ok) {
      return await handleResponse<ChatTurnResponse>(response)
    }
    if (!response.body) {
      throw new Error("Streaming response body is unavailable.")
    }

    reader = response.body.getReader()
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
      if (value?.length) resetStallTimeout()
      buffer += decoder.decode(value, { stream: !done })
      let boundary = buffer.indexOf("\n\n")
      while (boundary >= 0) {
        const block = buffer.slice(0, boundary).trim()
        buffer = buffer.slice(boundary + 2)
        if (block) consumeBlock(block)
        // The server emits this only after saving the answer and settling usage.
        if (completed) return completed
        boundary = buffer.indexOf("\n\n")
      }
      if (done) break
    }
    if (buffer.trim()) consumeBlock(buffer.trim())
    if (!completed) {
      throw new Error("AI stream ended before completion. Retry the same request to recover its result.")
    }
    return completed
  } catch (error) {
    if (timeoutReason && !options.signal?.aborted) {
      const message = timeoutReason === "stall" ? "AI stream stopped responding." : "AI request timed out."
      throw new Error(`${message} It may still be running; retry the same request to recover its result.`)
    }
    throw error
  } finally {
    clearTimeout(totalTimeoutId)
    clearTimeout(stallTimeoutId)
    controller.abort()
    if (reader) {
      try {
        await reader.cancel()
      } catch {
        // Aborted fetch readers may already have closed with an error.
      } finally {
        reader.releaseLock()
      }
    }
  }
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
