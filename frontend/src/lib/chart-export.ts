export const MAX_EXPORT_DIMENSION = 4096
export const MAX_EXPORT_PIXEL_AREA = 12_000_000
export const MAX_PIXEL_RATIO = 2

export function sanitizeExportFilename(value: string) {
  const sanitized = value
    .normalize("NFKC")
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "-")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^[.-]+|[.-]+$/g, "")
    .slice(0, 96)
  return sanitized || "personal-chart"
}

function includeInExport(node: HTMLElement) {
  return !node.hasAttribute?.("data-export-exclude")
}

export async function exportChartPng(target: HTMLElement, safeBaseFilename: string) {
  const width = Math.max(1, target.scrollWidth, target.clientWidth)
  const height = Math.max(1, target.scrollHeight, target.clientHeight)
  const logicalPixelArea = width * height
  const pixelRatio = Math.min(
    MAX_PIXEL_RATIO,
    MAX_EXPORT_DIMENSION / width,
    MAX_EXPORT_DIMENSION / height,
    Math.sqrt(MAX_EXPORT_PIXEL_AREA / logicalPixelArea),
  )
  const { toPng } = await import("html-to-image")
  const dataUrl = await toPng(target, {
    cacheBust: true,
    pixelRatio,
    filter: includeInExport,
    backgroundColor: getComputedStyle(target).backgroundColor,
  })

  const link = document.createElement("a")
  link.download = `${sanitizeExportFilename(safeBaseFilename)}.png`
  link.href = dataUrl
  document.body.appendChild(link)
  link.click()
  link.remove()
}

export function printChartPdf(target: HTMLElement, title: string) {
  const printWindow = window.open("", "_blank")
  if (!printWindow) throw new Error("print_window_blocked")
  printWindow.opener = null
  const styles = Array.from(document.querySelectorAll('link[rel="stylesheet"], style'))
    .map((node) => node.outerHTML)
    .join("\n")
  printWindow.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${title.replace(/[<>]/g, "")}</title>${styles}<style>@page{size:A4;margin:12mm}body{background:white!important;padding:0}.chart-share-canvas{width:100%!important;max-width:none!important;box-shadow:none!important;border:0!important}[data-export-exclude]{display:none!important}</style></head><body>${target.outerHTML}</body></html>`)
  printWindow.document.close()
  printWindow.addEventListener("load", () => {
    printWindow.focus()
    printWindow.print()
  }, { once: true })
}
