"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { SessionPayload } from "@/types/api"

const pad = (value: number) => value.toString().padStart(2, "0")
const formatDateInput = (date: Date) =>
  `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(
    date.getMinutes()
  )}`
const MODEL_ALIASES: Record<string, string> = {
  "gpt-5.1": "gpt-5.5",
  "gpt-5.2": "gpt-5.5",
  "gpt-5-mini": "gpt-5.4-mini",
}
const normalizeModelId = (model?: string | null) => (model ? MODEL_ALIASES[model] ?? model : "gpt-5.5")
const isResultsTab = (value: unknown): value is ResultsTab =>
  value === "summary" || value === "hex" || value === "ai"

export type WorkspaceForm = {
  topic: string
  userQuestion: string
  userContext: string
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
export type ResultsTab = "summary" | "hex" | "ai"
export type JournalStatus = "open" | "watching" | "resolved"

export type ReadingJournalEntry = {
  status: JournalStatus
  pinned: boolean
  outcomeNote: string
  revisitAt?: string
  updatedAt?: string
}

type WorkspaceState = {
  form: WorkspaceForm
  result?: SessionPayload
  history: SessionPayload[]
  journal: Record<string, ReadingJournalEntry>
  view: WorkspaceView
  resultsTab: ResultsTab
  lastSessionId?: string
  pendingChatPrompt?: string
  updateForm: <K extends keyof WorkspaceForm>(key: K, value: WorkspaceForm[K]) => void
  setForm: (values: Partial<WorkspaceForm>) => void
  resetForm: () => void
  setResult: (payload: SessionPayload) => void
  resetSession: () => void
  setView: (view: WorkspaceView) => void
  setResultsTab: (tab: ResultsTab) => void
  setPendingChatPrompt: (prompt?: string) => void
  updateJournal: (sessionId: string, patch: Partial<ReadingJournalEntry>) => void
  reopenResults: () => void
}

const defaultForm: WorkspaceForm = {
  topic: "事业",
  userQuestion: "",
  userContext: "",
  methodKey: "s",
  manualLines: "",
  useCurrentTime: true,
  customTimestamp: formatDateInput(new Date()),
  enableAi: false,
  accessPassword: "",
  aiModel: "gpt-5.5",
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
      journal: {},
      view: "form",
      resultsTab: "summary",
      lastSessionId: undefined,
      pendingChatPrompt: undefined,
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
            resultsTab: "summary",
            lastSessionId: payload.session_id,
            pendingChatPrompt: undefined,
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
          resultsTab: "summary",
          lastSessionId: undefined,
          pendingChatPrompt: undefined,
        }),
      setView: (view) => set({ view }),
      setResultsTab: (tab) => set({ resultsTab: tab }),
      setPendingChatPrompt: (prompt) => set({ pendingChatPrompt: prompt }),
      updateJournal: (sessionId, patch) =>
        set((state) => {
          const current = state.journal[sessionId] ?? {
            status: "open",
            pinned: false,
            outcomeNote: "",
          }
          return {
            journal: {
              ...state.journal,
              [sessionId]: {
                ...current,
                ...patch,
                updatedAt: new Date().toISOString(),
              },
            },
          }
        }),
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
        journal: state.journal,
        view: state.view,
        resultsTab: state.resultsTab,
        lastSessionId: state.lastSessionId,
        pendingChatPrompt: state.pendingChatPrompt,
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
          state.form = {
            ...defaultForm,
            ...state.form,
          }
          state.form.aiModel = normalizeModelId(state.form.aiModel)
        }
        if (state && !state.journal) {
          state.journal = {}
        }
        if (state && !isResultsTab(state.resultsTab)) {
          state.resultsTab = "summary"
        }
      },
    },
  ),
)
