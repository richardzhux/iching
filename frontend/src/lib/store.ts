"use client"

import { create } from "zustand"
import type { SessionPayload } from "@/types/api"

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
}

type WorkspaceState = {
  form: WorkspaceForm
  result?: SessionPayload
  history: SessionPayload[]
  updateForm: <K extends keyof WorkspaceForm>(key: K, value: WorkspaceForm[K]) => void
  setForm: (values: Partial<WorkspaceForm>) => void
  resetForm: () => void
  setResult: (payload: SessionPayload) => void
}

const defaultForm: WorkspaceForm = {
  topic: "",
  userQuestion: "",
  methodKey: "",
  manualLines: "",
  useCurrentTime: true,
  customTimestamp: new Date().toISOString().slice(0, 16),
  enableAi: false,
  accessPassword: "",
  aiModel: "gpt-5-nano",
  aiReasoning: null,
  aiVerbosity: null,
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  form: defaultForm,
  result: undefined,
  history: [],
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
        customTimestamp: new Date().toISOString().slice(0, 16),
      },
    }),
  setResult: (payload) =>
    set((state) => ({
      result: payload,
      history: [payload, ...state.history].slice(0, 10),
    })),
}))
