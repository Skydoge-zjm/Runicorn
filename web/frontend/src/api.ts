import type { RemoteStorageCandidate } from './types/remote'

const BASE_URL: string = (import.meta as any).env?.VITE_API_BASE || '/api'
const url = (p: string) => `${BASE_URL}${p}`

/** Unified fetch wrapper: handles error extraction and JSON parsing. */
async function apiFetch<T = any>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url(path), init)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

const JSON_HEADERS = { 'Content-Type': 'application/json' } as const

export async function listRuns() {
  return apiFetch('/runs')
}

export async function getRunDetail(id: string) {
  return apiFetch(`/runs/${id}`)
}

export async function getRunAssets(id: string) {
  return apiFetch(`/runs/${id}/assets`)
}

export interface RunImage {
  step: number | null
  key: string
  path: string
}

export async function getRunImages(id: string): Promise<{ run_id: string; images: RunImage[] }> {
  return apiFetch(`/runs/${id}/images`)
}

export function downloadRunAssetUrl(runId: string, absolutePath: string, filename?: string) {
  const qs = new URLSearchParams({ path: absolutePath })
  if (filename) qs.set('filename', filename)
  return url(`/runs/${runId}/assets/download?${qs.toString()}`)
}

export async function getMetrics(id: string, downsample?: number) {
  const params = downsample ? `?downsample=${downsample}` : ''
  return apiFetch(`/runs/${id}/metrics${params}`)
}

export async function getStepMetrics(id: string, downsample?: number) {
  const params = downsample ? `?downsample=${downsample}` : ''
  return apiFetch(`/runs/${id}/metrics_step${params}`)
}

export async function getProgress(id: string) {
  return apiFetch(`/runs/${id}/progress`)
}

export async function health() {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 3000) // 3 second timeout
  
  try {
    const res = await fetch(url('/health'), {
      signal: controller.signal,
      // Add cache: 'no-store' to prevent caching issues
      cache: 'no-store'
    })
    clearTimeout(timeoutId)
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  } catch (error) {
    clearTimeout(timeoutId)
    throw error
  }
}

export async function getGpuTelemetry() {
  return apiFetch('/gpu/telemetry')
}

export async function getGpuTelemetryHistory() {
  return apiFetch<{ available: boolean; enabled: boolean; samples: any[] }>('/gpu/telemetry/history')
}

export interface GpuCollectorConfig {
  enabled: boolean
  interval_sec: number
  max_duration_h: number
}

export async function getGpuTelemetryConfig() {
  return apiFetch<GpuCollectorConfig>('/gpu/telemetry/config')
}

export async function setGpuTelemetryConfig(patch: Partial<GpuCollectorConfig>) {
  return apiFetch<{ ok: boolean } & GpuCollectorConfig>('/gpu/telemetry/config', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(patch),
  })
}

export async function getSystemMonitor() {
  return apiFetch('/system/monitor')
}

// ----- New hierarchy helpers -----
export async function listProjects() {
  return apiFetch<{ projects: string[] }>('/projects')
}

export async function listNames(project: string) {
  return apiFetch<{ names: string[] }>(`/projects/${encodeURIComponent(project)}/names`)
}

export async function listRunsByName(project: string, name: string) {
  return apiFetch(`/projects/${encodeURIComponent(project)}/names/${encodeURIComponent(name)}/runs`)
}

// ----- Config helpers -----
export async function getConfig() {
  return apiFetch<{
    user_root_dir: string
    storage: string
    home_directory?: string
    storage_backend?: {
      mode: 'sqlite' | 'file'
      label: string
      available: boolean
      backend_class?: string | null
    }
  }>('/config')
}

export async function setUserRootDir(path: string) {
  return apiFetch<{ ok: boolean; user_root_dir: string; storage: string }>('/config/user_root_dir', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ path }),
  })
}

export async function listLocalStorageCandidates(
  scanRoot?: string,
  maxDepth: number = 3,
): Promise<RemoteStorageCandidate[]> {
  const params = new URLSearchParams({ max_depth: String(maxDepth) })
  if (scanRoot) {
    params.set('scan_root', scanRoot)
  }

  const data = await apiFetch<{ candidates?: Array<any> }>(`/config/storage-candidates?${params.toString()}`)
  return (data.candidates || []).map((item: any) => ({
    path: item.path,
    runCount: item.run_count ?? item.runCount ?? 0,
    hasArchive: Boolean(item.has_archive ?? item.hasArchive),
    hasIndex: Boolean(item.has_index ?? item.hasIndex),
  }))
}

// SSH connection config APIs
interface SavedSSHConnection {
  key: string
  host: string
  port: number
  username: string
  name?: string
  auth_method: string
  private_key_path?: string
  has_password?: boolean
  has_private_key?: boolean
}

interface SaveSSHConnectionPayload {
  host: string
  port: number
  username: string
  name?: string
  auth_method: string
  remember_password: boolean
  password?: string
  private_key?: string
  private_key_path?: string
  passphrase?: string
}

export async function getSavedSSHConnections() {
  return apiFetch<{ connections: SavedSSHConnection[] }>('/config/ssh_connections')
}

export async function saveSSHConnection(connection: SaveSSHConnectionPayload) {
  return apiFetch<{ ok: boolean; message: string }>('/config/ssh_connections', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(connection),
  })
}

export async function deleteSSHConnection(key: string) {
  return apiFetch<{ ok: boolean; message: string }>(`/config/ssh_connections/${encodeURIComponent(key)}`, {
    method: 'DELETE',
  })
}

export async function getSSHConnectionDetails(key: string) {
  return apiFetch<{ ok: boolean; connection: any }>(`/config/ssh_connections/${encodeURIComponent(key)}/details`)
}

export async function exportRunsZip(runIds: string[]) {
  const res = await fetch(url('/runs/export'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_ids: runIds }),
  })
  if (!res.ok) throw new Error(await res.text())
  const blob = await res.blob()
  const downloadUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = downloadUrl
  const disposition = res.headers.get('content-disposition')
  const match = disposition?.match(/filename="?([^"]+)"?/)
  const ts = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '').replace(/(\d{8})(\d{6})/, '$1_$2')
  a.download = match?.[1] || `runicorn_export_${runIds.length}runs_${ts}.zip`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(downloadUrl)
}

export interface ImportPreviewResult {
  ok: boolean
  token: string
  filename: string
  runs: { run_id: string; path: string; files_count: number; conflict: boolean }[]
  total_runs: number
  total_files: number
  conflict_count: number
  conflict_run_ids: string[]
}

export async function previewImport(file: File): Promise<ImportPreviewResult> {
  const fd = new FormData()
  fd.append('file', file)
  return apiFetch('/import/preview', { method: 'POST', body: fd })
}

export interface ImportArchiveResult {
  ok: boolean
  imported_files: number
  new_run_dirs: string[]
  new_run_ids: string[]
  skipped_run_ids: string[]
  skipped_count: number
  storage: string
  mode: string
  isolate_base: string | null
}

export async function confirmImport(previewToken: string, mode: 'merge' | 'isolate'): Promise<ImportArchiveResult> {
  const fd = new FormData()
  fd.append('preview_token', previewToken)
  fd.append('mode', mode)
  return apiFetch('/import/archive', { method: 'POST', body: fd })
}

/** Legacy: direct import without preview (backwards compat) */
export async function importArchive(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('mode', 'merge')
  return apiFetch<ImportArchiveResult>('/import/archive', { method: 'POST', body: fd })
}

// ----- Unified SSH helpers -----
export async function unifiedConnect(payload: {
  host: string; port?: number; username: string; password?: string;
  private_key?: string; private_key_path?: string; passphrase?: string; use_agent?: boolean;
}) {
  return apiFetch('/unified/connect', { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(payload) })
}

export async function unifiedDisconnect() {
  return apiFetch('/unified/disconnect', { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({}) })
}

export async function unifiedStatus() {
  return apiFetch('/unified/status')
}

export async function unifiedConfigureMode(payload: {
  mode: 'smart' | 'mirror'; remote_root?: string; auto_sync?: boolean;
  sync_interval_seconds?: number; mirror_interval?: number;
}) {
  return apiFetch('/unified/configure_mode', { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(payload) })
}

export async function unifiedDeactivateMode(mode: 'smart' | 'mirror') {
  return apiFetch('/unified/deactivate_mode', { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ mode }) })
}

export async function unifiedListdir(path?: string) {
  const q = new URLSearchParams({ path: path || '' })
  return apiFetch<{
    items: Array<{ name: string; path: string; type: 'dir'|'file'|'unknown'; size: number; mtime: number }>;
    current_path: string; ok: boolean;
  }>(`/unified/listdir?${q.toString()}`)
}

// ----- SSH live sync helpers -----
export async function sshConnect(payload: {
  host: string; port?: number; username: string; password?: string;
  pkey?: string; pkey_path?: string; passphrase?: string; use_agent?: boolean;
}) {
  return apiFetch<{ ok: boolean; session_id: string }>('/ssh/connect', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(payload),
  })
}

export async function sshSessions() {
  return apiFetch<{ sessions: Array<{ id: string; host: string; port: number; username: string }> }>('/ssh/sessions')
}

export async function sshClose(session_id: string) {
  return apiFetch<{ ok: boolean }>('/ssh/close', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ session_id }),
  })
}

export async function sshListdir(session_id: string, path?: string) {
  const q = new URLSearchParams({ session_id, path: path || '' })
  return apiFetch<{ items: Array<{ name: string; path: string; type: 'dir'|'file'; size: number; mtime: number }> }>(`/ssh/listdir?${q.toString()}`)
}

export async function sshMirrorStart(payload: { session_id: string; remote_root: string; interval?: number }) {
  return apiFetch<{ ok: boolean; task: any }>('/ssh/mirror/start', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(payload),
  })
}

export async function sshMirrorStop(task_id: string) {
  return apiFetch<{ ok: boolean }>('/ssh/mirror/stop', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ task_id }),
  })
}

export async function sshMirrorList() {
  return apiFetch<{ mirrors: any[]; storage: string }>('/ssh/mirror/list')
}

// ----- Status management -----
export async function checkAllStatus() {
  return apiFetch<{ checked: number; updated: number; message: string }>('/status/check', {
    method: 'POST', headers: JSON_HEADERS,
  })
}

// ----- Soft delete / Recycle bin -----
export async function softDeleteRuns(runIds: string[]) {
  return apiFetch<{ deleted_count: number; results: Record<string, any>; message: string }>('/runs/soft-delete', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ run_ids: runIds }),
  })
}

export async function listDeletedRuns() {
  return apiFetch<{ deleted_runs: Array<{
    id: string; path: string; alias: string | null; created_time: number;
    deleted_at: number; delete_reason: string; original_status: string; run_dir: string;
  }> }>('/recycle-bin')
}

export async function restoreRuns(runIds: string[]) {
  return apiFetch<{ restored_count: number; results: Record<string, any>; message: string }>('/recycle-bin/restore', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ run_ids: runIds }),
  })
}

export async function emptyRecycleBin() {
  return apiFetch<{ permanently_deleted: number; message: string }>('/recycle-bin/empty', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ confirm: true }),
  })
}

// ----- Permanent delete with asset cleanup -----
export interface AssetRefInfo {
  asset_id: string
  asset_type: string
  name: string | null
  fingerprint: string | null
  role: string
  ref_count: number
  other_runs?: string[]
}

export interface RunAssetRefs {
  run_id: string
  orphaned_assets: AssetRefInfo[]
  shared_assets: AssetRefInfo[]
  orphaned_count: number
  shared_count: number
}

export interface PermanentDeleteResult {
  success: boolean
  run_id: string
  run_dir_deleted: boolean
  orphaned_assets: Array<{
    asset_id: string
    asset_type: string
    name: string | null
    fingerprint: string | null
    role: string
  }>
  kept_assets: Array<{
    asset_id: string
    asset_type: string
    name: string | null
    fingerprint: string | null
    role: string
  }>
  blobs_deleted: number
  manifests_deleted: number
  bytes_freed: number
  errors: string[]
}

export async function getRunAssetRefs(runId: string): Promise<RunAssetRefs> {
  return apiFetch(`/runs/${runId}/assets/refs`)
}

export async function permanentDeleteRun(runId: string, dryRun: boolean = false): Promise<PermanentDeleteResult> {
  return apiFetch(`/runs/${runId}/permanent?dry_run=${dryRun}`, { method: 'DELETE' })
}

export async function permanentDeleteRunsBatch(runIds: string[], dryRun: boolean = false) {
  return apiFetch<{
    deleted_count: number; total_runs: number; total_blobs_deleted: number;
    total_bytes_freed: number; dry_run: boolean; results: Record<string, PermanentDeleteResult>;
  }>('/runs/permanent-delete', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ run_ids: runIds, dry_run: dryRun }),
  })
}

// ----- Storage stats -----
export interface StorageStats {
  storage_root: string
  total: {
    size_bytes: number
    size_human: string
  }
  archive: {
    size_bytes: number
    size_human: string
    blobs: {
      size_bytes: number
      size_human: string
      file_count: number
    }
    manifests: {
      size_bytes: number
      size_human: string
      file_count: number
      by_category: Record<string, {
        size_bytes: number
        size_human: string
        file_count: number
      }>
    }
    outputs: {
      size_bytes: number
      size_human: string
      file_count: number
    }
  }
  runs: {
    size_bytes: number
    size_human: string
    projects_count: number
    experiments_count: number
    runs_count: number
  }
  index: {
    size_bytes: number
    size_human: string
  }
}

export async function getStorageStats(): Promise<StorageStats> {
  return apiFetch('/storage/stats')
}

// ----- Run update helpers -----
export async function updateRunAlias(runId: string, alias: string | null) {
  return apiFetch<{ ok: boolean; alias: string | null }>(`/runs/${runId}`, {
    method: 'PATCH', headers: JSON_HEADERS, body: JSON.stringify({ alias }),
  })
}

export async function updateRunTags(runId: string, tags: string[]) {
  return apiFetch<{ ok: boolean; tags: string[] }>(`/runs/${runId}`, {
    method: 'PATCH', headers: JSON_HEADERS, body: JSON.stringify({ tags }),
  })
}

// ----- Move runs -----
export async function moveRuns(runIds: string[], targetPath: string) {
  return apiFetch<{
    ok: boolean; moved_count: number; failed_count: number;
    moved: Array<{ run_id: string; old_path: string; new_path: string }>;
    failed: Array<{ run_id: string; error: string }>;
  }>('/runs/move', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ run_ids: runIds, target_path: targetPath }),
  })
}

// ----- Path helpers -----
export async function softDeleteByPath(path: string) {
  return apiFetch<{ deleted_count: number }>('/paths/soft-delete', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ path }),
  })
}

export async function createPath(path: string) {
  return apiFetch<{ ok: boolean; path: string }>('/paths/create', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ path }),
  })
}

export async function listPaths(includeStats = true) {
  const qs = includeStats ? '?include_stats=true' : ''
  return apiFetch(`/paths${qs}`)
}

// ----- Column width config -----
export async function getColumnWidths(tableKey: string, sizeKey: string) {
  try {
    return await apiFetch(`/config/column-widths?table=${tableKey}&size=${sizeKey}`)
  } catch {
    return null
  }
}

export async function saveColumnWidths(payload: {
  table: string; size: string; widths: Record<string, number>;
  window_width: number; window_height: number;
}) {
  await apiFetch('/config/column-widths', {
    method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(payload),
  })
}
