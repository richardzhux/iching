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
