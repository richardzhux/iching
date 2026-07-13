"use client"

import { useState } from "react"
import { Download, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { exportChartPng } from "@/lib/chart-export"

type Props = {
  targetId: string
  label: string
  loadingLabel: string
  errorLabel: string
  safeBaseFilename: string
}

export function ChartExportButton({ targetId, label, loadingLabel, errorLabel, safeBaseFilename }: Props) {
  const [exporting, setExporting] = useState(false)

  async function handleExport() {
    const target = document.getElementById(targetId)
    if (!target) {
      toast.error(errorLabel)
      return
    }
    setExporting(true)
    try {
      await exportChartPng(target, safeBaseFilename)
    } catch {
      toast.error(errorLabel)
    } finally {
      setExporting(false)
    }
  }

  return (
    <>
      <Button
        type="button"
        variant="outline"
        onClick={handleExport}
        disabled={exporting}
        aria-label={exporting ? loadingLabel : label}
        data-export-exclude
      >
        {exporting ? <Loader2 aria-hidden="true" className="mr-2 size-4 animate-spin" /> : <Download aria-hidden="true" className="mr-2 size-4" />}
        <span>{exporting ? loadingLabel : label}</span>
      </Button>
      <span role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {exporting ? loadingLabel : label}
      </span>
    </>
  )
}
