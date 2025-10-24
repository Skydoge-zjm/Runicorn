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

export async function getMetrics(id: string) {
  const res = await fetch(url(`/runs/${id}/metrics`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getStepMetrics(id: string) {
  const res = await fetch(url(`/runs/${id}/metrics_step`))
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

export async function importArchive(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(url('/import/archive'), {
    method: 'POST',
    body: fd
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{
    ok: boolean
    imported_files: number
    new_run_dirs: string[]
    new_run_ids: string[]
    storage: string
  }>
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
    project: string
    name: string
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

// ========== Artifacts API ==========

export async function listArtifacts(type?: string) {
  const q = type ? `?type=${type}` : ''
  const res = await fetch(url(`/artifacts${q}`))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<any[]>
}

export async function listArtifactVersions(name: string, type?: string) {
  const q = type ? `?type=${type}` : ''
  const res = await fetch(url(`/artifacts/${name}/versions${q}`))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<any[]>
}

export async function getArtifactDetail(name: string, version: number, type?: string) {
  const q = type ? `?type=${type}` : ''
  const res = await fetch(url(`/artifacts/${name}/v${version}${q}`))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<any>
}

export async function getArtifactFiles(name: string, version: number, type?: string) {
  const q = type ? `?type=${type}` : ''
  const res = await fetch(url(`/artifacts/${name}/v${version}/files${q}`))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ files: any[]; references: any[]; total_size: number }>
}

export async function getArtifactLineage(
  name: string, 
  version: number, 
  type?: string,
  maxDepth: number = 3
) {
  const params = new URLSearchParams({ max_depth: maxDepth.toString() })
  if (type) params.set('type', type)
  const res = await fetch(url(`/artifacts/${name}/v${version}/lineage?${params.toString()}`))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ root_artifact: string; nodes: any[]; edges: any[] }>
}

export async function getArtifactsStats() {
  const res = await fetch(url('/artifacts/stats'))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<any>
}

export async function deleteArtifactVersion(
  name: string, 
  version: number, 
  type?: string,
  permanent: boolean = false
) {
  const params = new URLSearchParams({ permanent: permanent.toString() })
  if (type) params.set('type', type)
  const res = await fetch(url(`/artifacts/${name}/v${version}?${params.toString()}`), {
    method: 'DELETE'
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ success: boolean; message: string }>
}

// ========== Remote Storage API ==========

// ----- Connection Management -----
export interface RemoteConfig {
  host: string
  port: number
  username: string
  password?: string
  private_key?: string
  private_key_path?: string
  passphrase?: string
  use_agent: boolean
  remote_root: string
  auto_sync: boolean
  sync_interval_seconds: number
}

export async function remoteConnect(config: RemoteConfig) {
  const res = await fetch(url('/remote/connect'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{
    ok: boolean
    status: string
    host: string
    username: string
    remote_root: string
    cache_dir: string
    structure_verified: Record<string, boolean>
    auto_sync: boolean
    sync_interval_seconds: number
  }>
}

export async function remoteDisconnect() {
  const res = await fetch(url('/remote/disconnect'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; status: string; message: string }>
}

export async function getRemoteStatus() {
  const res = await fetch(url('/remote/status'))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{
    mode: string
    connected: boolean
    status: string
    sync_progress?: {
      status: string
      started_at?: number
      completed_at?: number
      total_files: number
      synced_files: number
      total_bytes: number
      synced_bytes: number
      current_file: string
      progress_percent: number
      errors: string[]
    }
    stats?: {
      connected: boolean
      last_sync?: number
      total_artifacts: number
      cached_artifacts: number
      cache_size_bytes: number
      remote_size_bytes: number
      sync_count: number
      error_count: number
    }
  }>
}

export async function getStorageMode() {
  const res = await fetch(url('/remote/mode'))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{
    mode: string
    remote_available: boolean
    remote_connected: boolean
  }>
}

export async function switchStorageMode(mode: 'local' | 'remote') {
  const res = await fetch(url('/remote/mode/switch'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; mode: string; message: string }>
}

// ----- Metadata Synchronization -----
export async function remoteSyncMetadata() {
  const res = await fetch(url('/remote/sync'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; message: string; info: string }>
}

// ----- File Downloads -----
export async function remoteDownloadArtifact(
  name: string,
  version: number,
  type?: string,
  targetDir?: string
) {
  const params = new URLSearchParams()
  if (type) params.set('type', type)
  
  const body = targetDir ? JSON.stringify({ target_dir: targetDir }) : null
  
  const res = await fetch(url(`/remote/download/${name}/v${version}?${params.toString()}`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{
    ok: boolean
    task_id: string
    artifact: string
    message: string
  }>
}

export async function getDownloadStatus(taskId: string) {
  const res = await fetch(url(`/remote/download/${taskId}/status`))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{
    task_id: string
    artifact_name: string
    artifact_type: string
    artifact_version: number
    target_dir: string
    total_files: number
    downloaded_files: number
    total_bytes: number
    downloaded_bytes: number
    progress_percent: number
    status: string
    error?: string
  }>
}

export async function cancelDownload(taskId: string) {
  const res = await fetch(url(`/remote/download/${taskId}`), {
    method: 'DELETE'
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; message: string }>
}

export async function listDownloads() {
  const res = await fetch(url('/remote/downloads'))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{
    downloads: Array<any>
    active_count: number
    total_count: number
  }>
}

// ----- Cache Management -----
export async function clearRemoteCache() {
  const res = await fetch(url('/remote/cache/clear'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; message: string }>
}

export async function cleanupRemoteCache() {
  const res = await fetch(url('/remote/cache/cleanup'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; files_removed: number; message: string }>
}

// ----- Remote Operations -----
export async function setRemoteAlias(
  name: string,
  version: number,
  alias: string,
  type?: string
) {
  const params = new URLSearchParams()
  if (type) params.set('type', type)
  
  const res = await fetch(url(`/remote/artifacts/${name}/v${version}/alias?${params.toString()}`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alias })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; message: string }>
}

export async function addRemoteTags(
  name: string,
  version: number,
  tags: string[],
  type?: string
) {
  const params = new URLSearchParams()
  if (type) params.set('type', type)
  
  const res = await fetch(url(`/remote/artifacts/${name}/v${version}/tags?${params.toString()}`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tags })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ ok: boolean; message: string }>
}

// ----- Diagnostics -----
export async function verifyRemoteConnection() {
  const res = await fetch(url('/remote/verify'))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{
    connected: boolean
    structure?: Record<string, boolean>
    adapter_status?: string
    error?: string
  }>
}
