import type { DiagnosticsSourcesResponse } from '../types/diagnostics'

function getApiBase(): string {
  return ((import.meta as any).env?.VITE_API_BASE || '/api') as string
}

function buildHttpUrl(path: string, params?: URLSearchParams): string {
  const base = getApiBase().replace(/\/$/, '')
  const suffix = params && params.toString() ? `?${params.toString()}` : ''
  if (/^https?:/i.test(base)) {
    return `${base}${path}${suffix}`
  }
  return `${base}${path}${suffix}`
}

export function buildDiagnosticsWsUrl(sourceId: string, lines: number = 400): string {
  const base = getApiBase().replace(/\/$/, '')
  const params = new URLSearchParams({
    source: sourceId,
    lines: String(lines),
  })
  const suffix = `?${params.toString()}`
  const wsProto = location.protocol === 'https:' ? 'wss' : 'ws'
  if (/^https?:/i.test(base)) {
    return `${base.replace(/^http/i, wsProto)}/diagnostics/logs/ws${suffix}`
  }
  return `${wsProto}://${location.host}${base}/diagnostics/logs/ws${suffix}`
}

export function buildDiagnosticsDownloadUrl(sourceId: string): string {
  const params = new URLSearchParams({
    source: sourceId,
    download: 'true',
  })
  return buildHttpUrl('/diagnostics/logs', params)
}

export async function listDiagnosticsSources(): Promise<DiagnosticsSourcesResponse> {
  const response = await fetch(buildHttpUrl('/diagnostics/sources'), {
    cache: 'no-store',
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(detail || 'Failed to load diagnostics sources')
  }
  return response.json()
}
