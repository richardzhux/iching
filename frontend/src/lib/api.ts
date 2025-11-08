import type { ConfigResponse, SessionPayload, SessionRequest } from "@/types/api"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = "请求失败，请稍后再试。"
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
  const response = await fetch(`${API_BASE}/api/config`, {
    cache: "no-store",
  })
  return handleResponse<ConfigResponse>(response)
}

export async function createSession(request: SessionRequest): Promise<SessionPayload> {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  })
  return handleResponse<SessionPayload>(response)
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
    throw new Error("手动六爻需要 6 个数字")
  }

  const values = tokens.map((token) => {
    const value = Number(token)
    if (![6, 7, 8, 9].includes(value)) {
      throw new Error("每一爻必须是 6 / 7 / 8 / 9")
    }
    return value
  })

  return values
}
