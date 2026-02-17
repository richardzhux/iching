"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { SessionPayload } from "@/types/api"

const pad = (value: number) => value.toString().padStart(2, "0")
const formatDateInput = (date: Date) =>
  `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(
    date.getMinutes()
  )}`
const normalizeModelId = (model?: string | null) => (model === "gpt-5.1" ? "gpt-5.2" : model ?? "gpt-5.2")

export type WorkspaceForm = {
  topic: string
  userQuestion: string
  methodKey: string
  manualLines: string
  useCurrentTime: boolean
  customTimestamp: string
  enableAi: boolean
  accessPassword: string
  aiModel: string
  aiReasoning?: string | null
  aiVerbosity?: string | null
  aiTone: string
}

export type WorkspaceView = "form" | "results"

type WorkspaceState = {
  form: WorkspaceForm
  result?: SessionPayload
  history: SessionPayload[]
  view: WorkspaceView
  lastSessionId?: string
  updateForm: <K extends keyof WorkspaceForm>(key: K, value: WorkspaceForm[K]) => void
  setForm: (values: Partial<WorkspaceForm>) => void
  resetForm: () => void
  setResult: (payload: SessionPayload) => void
  resetSession: () => void
  setView: (view: WorkspaceView) => void
  reopenResults: () => void
}

const defaultForm: WorkspaceForm = {
  topic: "事业",
  userQuestion: "",
  methodKey: "s",
  manualLines: "",
  useCurrentTime: true,
  customTimestamp: formatDateInput(new Date()),
  enableAi: false,
  accessPassword: "",
  aiModel: "gpt-5.2",
  aiReasoning: null,
  aiVerbosity: null,
  aiTone: "normal",
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      form: defaultForm,
      result: undefined,
      history: [],
      view: "form",
      lastSessionId: undefined,
      updateForm: (key, value) =>
        set((state) => ({
          form: {
            ...state.form,
            [key]: value,
          },
        })),
      setForm: (values) =>
        set((state) => ({
          form: {
            ...state.form,
            ...values,
          },
        })),
      resetForm: () =>
        set({
          form: {
            ...defaultForm,
            customTimestamp: formatDateInput(new Date()),
          },
        }),
      setResult: (payload) =>
        set((state) => {
          const existing = (state.history ?? []).filter(
            (entry) => entry.session_id !== payload.session_id,
          )
          const nextHistory = [payload, ...existing].slice(0, 10)
          return {
            result: payload,
            history: nextHistory,
            view: "results",
            lastSessionId: payload.session_id,
          }
        }),
      resetSession: () =>
        set({
          form: {
            ...defaultForm,
            customTimestamp: formatDateInput(new Date()),
          },
          result: undefined,
          view: "form",
          lastSessionId: undefined,
        }),
      setView: (view) => set({ view }),
      reopenResults: () =>
        set((state) => (state.result ? { view: "results" } : state)),
    }),
    {
      name: "iching-workspace",
      version: 1,
      partialize: (state) => ({
        form: state.form,
        result: state.result,
        history: state.history,
        view: state.view,
        lastSessionId: state.lastSessionId,
      }),
      onRehydrateStorage: () => (state) => {
        if (state && !state.form?.customTimestamp) {
          state.form = {
            ...defaultForm,
            ...state.form,
            aiModel: normalizeModelId(state.form?.aiModel),
            customTimestamp: formatDateInput(new Date()),
          }
        } else if (state?.form) {
          state.form.aiModel = normalizeModelId(state.form.aiModel)
        }
      },
    },
  ),
)
