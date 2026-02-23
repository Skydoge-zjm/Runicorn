const BASE_URL: string = (import.meta as any).env?.VITE_API_BASE || '/api'
const url = (p: string) => `${BASE_URL}${p}`

export async function listRuns() {
  const res = await fetch(url('/runs'))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getRunDetail(id: string) {
  const res = await fetch(url(`/runs/${id}`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getRunAssets(id: string) {
  const res = await fetch(url(`/runs/${id}/assets`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function downloadRunAssetUrl(runId: string, absolutePath: string, filename?: string) {
  const qs = new URLSearchParams({ path: absolutePath })
  if (filename) qs.set('filename', filename)
  return url(`/runs/${runId}/assets/download?${qs.toString()}`)
}

export async function getMetrics(id: string, downsample?: number) {
  const params = downsample ? `?downsample=${downsample}` : ''
  const res = await fetch(url(`/runs/${id}/metrics${params}`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getStepMetrics(id: string, downsample?: number) {
  const params = downsample ? `?downsample=${downsample}` : ''
  const res = await fetch(url(`/runs/${id}/metrics_step${params}`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getProgress(id: string) {
  const res = await fetch(url(`/runs/${id}/progress`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
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
  const res = await fetch(url('/gpu/telemetry'))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getSystemMonitor() {
  const res = await fetch(url('/system/monitor'))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ----- New hierarchy helpers -----
export async function listProjects() {
  const res = await fetch(url('/projects'))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ projects: string[] }>
}

export async function listNames(project: string) {
  const res = await fetch(url(`/projects/${encodeURIComponent(project)}/names`))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ names: string[] }>
}

export async function listRunsByName(project: string, name: string) {
  const res = await fetch(url(`/projects/${encodeURIComponent(project)}/names/${encodeURIComponent(name)}/runs`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ----- Config helpers -----
export async function getConfig() {
  const res = await fetch(url('/config'))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ user_root_dir: string; storage: string }>
}

export async function setUserRootDir(path: string) {
  const res = await fetch(url('/config/user_root_dir'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; user_root_dir: string; storage: string }>
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
  const res = await fetch(url('/config/ssh_connections'))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ connections: SavedSSHConnection[] }>
}

export async function saveSSHConnection(connection: SaveSSHConnectionPayload) {
  const res = await fetch(url('/config/ssh_connections'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(connection),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; message: string }>
}

export async function deleteSSHConnection(key: string) {
  const res = await fetch(url(`/config/ssh_connections/${encodeURIComponent(key)}`), {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; message: string }>
}

export async function getSSHConnectionDetails(key: string) {
  const res = await fetch(url(`/config/ssh_connections/${encodeURIComponent(key)}/details`))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; connection: any }>  
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
  const res = await fetch(url('/import/preview'), {
    method: 'POST',
    body: fd,
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
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
  const res = await fetch(url('/import/archive'), {
    method: 'POST',
    body: fd,
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/** Legacy: direct import without preview (backwards compat) */
export async function importArchive(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('mode', 'merge')
  const res = await fetch(url('/import/archive'), {
    method: 'POST',
    body: fd
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<ImportArchiveResult>
}

// ----- Unified SSH helpers -----
export async function unifiedConnect(payload: {
  host: string
  port?: number
  username: string
  password?: string
  private_key?: string
  private_key_path?: string
  passphrase?: string
  use_agent?: boolean
}) {
  const res = await fetch(url('/unified/connect'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function unifiedDisconnect() {
  const res = await fetch(url('/unified/disconnect'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function unifiedStatus() {
  const res = await fetch(url('/unified/status'))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function unifiedConfigureMode(payload: {
  mode: 'smart' | 'mirror'
  remote_root?: string
  auto_sync?: boolean
  sync_interval_seconds?: number
  mirror_interval?: number
}) {
  const res = await fetch(url('/unified/configure_mode'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function unifiedDeactivateMode(mode: 'smart' | 'mirror') {
  const res = await fetch(url('/unified/deactivate_mode'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function unifiedListdir(path?: string) {
  const q = new URLSearchParams({ path: path || '' })
  const res = await fetch(url(`/unified/listdir?${q.toString()}`))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ 
    items: Array<{ 
      name: string; 
      path: string; 
      type: 'dir'|'file'|'unknown'; 
      size: number; 
      mtime: number 
    }>; 
    current_path: string;
    ok: boolean 
  }>
}

// ----- SSH live sync helpers -----
export async function sshConnect(payload: {
  host: string
  port?: number
  username: string
  password?: string
  pkey?: string
  pkey_path?: string
  passphrase?: string
  use_agent?: boolean
}) {
  const res = await fetch(url('/ssh/connect'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; session_id: string }>
}

export async function sshSessions() {
  const res = await fetch(url('/ssh/sessions'))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ sessions: Array<{ id: string; host: string; port: number; username: string }> }>
}

export async function sshClose(session_id: string) {
  const res = await fetch(url('/ssh/close'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean }>
}

export async function sshListdir(session_id: string, path?: string) {
  const q = new URLSearchParams({ session_id, path: path || '' })
  const res = await fetch(url(`/ssh/listdir?${q.toString()}`))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ items: Array<{ name: string; path: string; type: 'dir'|'file'; size: number; mtime: number }> }>
}

export async function sshMirrorStart(payload: { session_id: string; remote_root: string; interval?: number }) {
  const res = await fetch(url('/ssh/mirror/start'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; task: any }>
}

export async function sshMirrorStop(task_id: string) {
  const res = await fetch(url('/ssh/mirror/stop'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean }>
}

export async function sshMirrorList() {
  const res = await fetch(url('/ssh/mirror/list'))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ mirrors: any[]; storage: string }>
}

// ----- Status management -----
export async function checkAllStatus() {
  const res = await fetch(url('/status/check'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ checked: number; updated: number; message: string }>
}

// ----- Soft delete / Recycle bin -----
export async function softDeleteRuns(runIds: string[]) {
  const res = await fetch(url('/runs/soft-delete'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_ids: runIds })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ deleted_count: number; results: Record<string, any>; message: string }>
}

export async function listDeletedRuns() {
  const res = await fetch(url('/recycle-bin'))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ deleted_runs: Array<{
    id: string
    path: string
    alias: string | null
    created_time: number
    deleted_at: number
    delete_reason: string
    original_status: string
    run_dir: string
  }> }>
}

export async function restoreRuns(runIds: string[]) {
  const res = await fetch(url('/recycle-bin/restore'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_ids: runIds })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ restored_count: number; results: Record<string, any>; message: string }>
}

export async function emptyRecycleBin() {
  const res = await fetch(url('/recycle-bin/empty'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirm: true })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ permanently_deleted: number; message: string }>
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
  const res = await fetch(url(`/runs/${runId}/assets/refs`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function permanentDeleteRun(runId: string, dryRun: boolean = false): Promise<PermanentDeleteResult> {
  const res = await fetch(url(`/runs/${runId}/permanent?dry_run=${dryRun}`), {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function permanentDeleteRunsBatch(runIds: string[], dryRun: boolean = false): Promise<{
  deleted_count: number
  total_runs: number
  total_blobs_deleted: number
  total_bytes_freed: number
  dry_run: boolean
  results: Record<string, PermanentDeleteResult>
}> {
  const res = await fetch(url('/runs/permanent-delete'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_ids: runIds, dry_run: dryRun })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
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
  const res = await fetch(url('/storage/stats'))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ----- Run update helpers -----
export async function updateRunAlias(runId: string, alias: string | null): Promise<{ ok: boolean; alias: string | null }> {
  const res = await fetch(url(`/runs/${runId}`), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alias })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateRunTags(runId: string, tags: string[]): Promise<{ ok: boolean; tags: string[] }> {
  const res = await fetch(url(`/runs/${runId}`), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tags })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ----- Move runs -----
export async function moveRuns(runIds: string[], targetPath: string) {
  const res = await fetch(url('/runs/move'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_ids: runIds, target_path: targetPath }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{
    ok: boolean
    moved_count: number
    failed_count: number
    moved: Array<{ run_id: string; old_path: string; new_path: string }>
    failed: Array<{ run_id: string; error: string }>
  }>
}

// ----- Path helpers -----
export async function softDeleteByPath(path: string) {
  const res = await fetch(url('/paths/soft-delete'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ deleted_count: number }>
}

export async function createPath(path: string) {
  const res = await fetch(url('/paths/create'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; path: string }>
}

export async function listPaths(includeStats = true) {
  const qs = includeStats ? '?include_stats=true' : ''
  const res = await fetch(url(`/paths${qs}`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ----- Column width config -----
export async function getColumnWidths(tableKey: string, sizeKey: string) {
  const res = await fetch(url(`/config/column-widths?table=${tableKey}&size=${sizeKey}`))
  if (!res.ok) return null
  return res.json()
}

export async function saveColumnWidths(payload: {
  table: string; size: string; widths: Record<string, number>;
  window_width: number; window_height: number;
}) {
  await fetch(url('/config/column-widths'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
