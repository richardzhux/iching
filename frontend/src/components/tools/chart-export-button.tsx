"use client"

import { useState } from "react"
import { Clipboard, Download, FileText, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { exportChartPng, sanitizeExportFilename } from "@/lib/chart-export"

type Props = {
  targetId: string
  label: string
  loadingLabel: string
  errorLabel: string
  safeBaseFilename: string
  markdown?: string
}

export function ChartExportButton({ targetId, label, loadingLabel, errorLabel, safeBaseFilename, markdown }: Props) {
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

  function downloadMarkdown() {
    if (!markdown) return
    const url = URL.createObjectURL(new Blob([markdown], { type: "text/markdown;charset=utf-8" }))
    const link = document.createElement("a")
    link.download = `${sanitizeExportFilename(safeBaseFilename)}.md`
    link.href = url
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  async function copyMarkdown() {
    if (!markdown) return
    try {
      await navigator.clipboard.writeText(markdown)
      toast.success("Markdown 已复制")
    } catch {
      toast.error("复制失败，请改用下载。")
    }
  }

  return (
    <div className="flex flex-wrap justify-end gap-2" data-export-exclude>
      <Button
        type="button"
        variant="outline"
        onClick={handleExport}
        disabled={exporting}
        aria-label={exporting ? loadingLabel : label}
      >
        {exporting ? <Loader2 aria-hidden="true" className="mr-2 size-4 animate-spin" /> : <Download aria-hidden="true" className="mr-2 size-4" />}
        <span>{exporting ? loadingLabel : markdown ? `${label} PNG` : label}</span>
      </Button>
      {markdown ? <Button type="button" variant="outline" onClick={downloadMarkdown}><FileText aria-hidden="true" className="mr-2 size-4" />Markdown</Button> : null}
      {markdown ? <Button type="button" variant="ghost" onClick={() => void copyMarkdown()} aria-label="复制 Markdown"><Clipboard aria-hidden="true" className="size-4" /></Button> : null}
      <span role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {exporting ? loadingLabel : label}
      </span>
    </div>
  )
}
