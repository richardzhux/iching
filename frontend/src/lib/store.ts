"use client"

import { create } from "zustand"
import type { SessionPayload } from "@/types/api"

const pad = (value: number) => value.toString().padStart(2, "0")
const formatDateInput = (date: Date) =>
  `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(
    date.getMinutes()
  )}`

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
  customTimestamp: formatDateInput(new Date()),
  enableAi: false,
  accessPassword: "",
  aiModel: "gpt-5-nano",
  aiReasoning: null,
  aiVerbosity: null,
  aiTone: "normal",
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
        customTimestamp: formatDateInput(new Date()),
      },
    }),
  setResult: (payload) =>
    set((state) => ({
      result: payload,
      history: [payload, ...state.history].slice(0, 10),
    })),
}))
