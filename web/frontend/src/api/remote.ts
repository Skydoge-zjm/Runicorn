/**
 * Remote Viewer API
 * 
 * API client for VSCode Remote-like Remote Viewer functionality
 */

import type {
  SSHConnectionConfig,
  SSHSession,
  RemoteSession,
  RemoteFileEntry,
  ConnectionTestResult,
  KnownHostsAcceptRequest,
  KnownHostsEntry,
  KnownHostsRemoveRequest
} from '../types/remote'

import { ApiError } from '../types/remote'

const API_BASE = '/api/remote'

async function parseResponsePayload(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    try {
      return await response.json()
    } catch {
      return undefined
    }
  }

  try {
    const text = await response.text()
    return text || undefined
  } catch {
    return undefined
  }
}

async function parseResponseDetail(response: Response): Promise<unknown> {
  const payload = await parseResponsePayload(response)

  if (payload && typeof payload === 'object' && 'detail' in payload) {
    return (payload as { detail?: unknown }).detail
  }

  return payload
}

function getErrorMessage(detail: unknown, fallbackMessage: string): string {
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (detail && typeof detail === 'object') {
    const maybeMessage = (detail as { message?: unknown }).message
    if (typeof maybeMessage === 'string' && maybeMessage.trim()) {
      return maybeMessage
    }
  }

  return fallbackMessage
}

async function ensureOk(response: Response, fallbackMessage: string): Promise<void> {
  if (response.ok) {
    return
  }

  const detail = await parseResponseDetail(response)
  throw new ApiError(response.status, getErrorMessage(detail, fallbackMessage), detail)
}

/**
 * Get local runicorn version
 */
export async function getLocalVersion(): Promise<string> {
  const response = await fetch('/api/health')
  await ensureOk(response, 'Failed to get local version')
  const data = await response.json()
  return data.version || 'unknown'
}

/**
 * Connect to remote server via SSH
 */
export async function connectRemote(config: SSHConnectionConfig): Promise<SSHSession> {
  const response = await fetch(`${API_BASE}/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      host: config.host,
      port: config.port,
      username: config.username,
      password: config.password,
      private_key_path: config.privateKeyPath,
      passphrase: config.passphrase,
      use_agent: true
    })
  })

  await ensureOk(response, 'Failed to connect to remote server')
  return response.json()
}

/**
 * Disconnect from remote server
 */
export async function disconnectRemote(host: string, port: number = 22, username: string): Promise<void> {
  const response = await fetch(`${API_BASE}/disconnect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ host, port, username })
  })

  await ensureOk(response, 'Failed to disconnect')
}

/**
 * List active SSH sessions
 */
export async function listSSHSessions(): Promise<SSHSession[]> {
  const response = await fetch(`${API_BASE}/sessions`)
  await ensureOk(response, 'Failed to list SSH sessions')
  const data = await response.json()
  return data.sessions || data
}

/**
 * Start Remote Viewer on remote server
 */
export async function startRemoteViewer(
  config: SSHConnectionConfig
): Promise<RemoteSession> {
  if (!config.remoteRoot) {
    throw new Error('Remote storage root is required')
  }

  const response = await fetch(`${API_BASE}/viewer/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      host: config.host,
      port: config.port,
      username: config.username,
      password: config.password,
      private_key_path: config.privateKeyPath,
      passphrase: config.passphrase,
      use_agent: true,
      remote_root: config.remoteRoot,
      local_port: config.localPort,
      remote_port: config.remotePort,
      conda_env: config.condaEnv
    })
  })

  await ensureOk(response, 'Failed to start Remote Viewer')
  return response.json()
}

/**
 * Stop Remote Viewer session
 */
export async function stopRemoteViewer(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/viewer/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId })
  })

  await ensureOk(response, 'Failed to stop Remote Viewer')
}

/**
 * List active Remote Viewer sessions
 */
export async function listRemoteSessions(): Promise<RemoteSession[]> {
  const response = await fetch(`${API_BASE}/viewer/sessions`)
  await ensureOk(response, 'Failed to list Remote Viewer sessions')
  const data = await response.json()
  return data.sessions || data
}

/**
 * Get Remote Viewer session status
 */
export async function getSessionStatus(sessionId: string): Promise<RemoteSession> {
  const response = await fetch(`${API_BASE}/viewer/status/${sessionId}`)
  await ensureOk(response, 'Failed to get session status')
  return response.json()
}

/**
 * Browse remote directory
 */
export async function browseRemoteDirectory(
  connectionId: string,
  path: string
): Promise<RemoteFileEntry[]> {
  const response = await fetch(
    `${API_BASE}/fs/list?connection_id=${encodeURIComponent(connectionId)}&path=${encodeURIComponent(path)}`
  )

  await ensureOk(response, 'Failed to list directory')

  return response.json()
}

/**
 * Test SSH connection (by actually connecting then disconnecting)
 */
export async function testConnection(config: SSHConnectionConfig): Promise<ConnectionTestResult> {
  try {
    // Test by connecting
    await connectRemote(config)
    
    // If successful, disconnect
    await disconnectRemote(config.host, config.port, config.username)
    
    return {
      success: true,
      responseTime: 0
    }
  } catch (error) {
    if (error instanceof ApiError) {
      // Propagate structured errors (e.g., host key confirmation)
      throw error
    }
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Connection test failed'
    }
  }
}

/**
 * List Runicorn-managed known hosts
 */
export async function listKnownHosts(): Promise<KnownHostsEntry[]> {
  const response = await fetch(`${API_BASE}/known-hosts/list`)
  await ensureOk(response, 'Failed to list known hosts')
  const data = await response.json()
  return (data.entries as KnownHostsEntry[]) || []
}

/**
 * Remove a specific host key entry from Runicorn known_hosts
 */
export async function removeKnownHost(payload: KnownHostsRemoveRequest): Promise<{ ok: boolean; changed: boolean }> {
  const response = await fetch(`${API_BASE}/known-hosts/remove`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  await ensureOk(response, 'Failed to remove known host')
  return response.json()
}

/**
 * List conda environments on remote server
 */
export async function listCondaEnvs(connectionId: string): Promise<any> {
  const response = await fetch(
    `${API_BASE}/conda-envs?connection_id=${encodeURIComponent(connectionId)}`
  )

  await ensureOk(response, 'Failed to list conda environments')

  return response.json()
}

/**
 * Get remote server runicorn configuration
 */
export async function getRemoteConfig(connectionId: string, condaEnv: string = 'system'): Promise<any> {
  const response = await fetch(
    `${API_BASE}/config?connection_id=${encodeURIComponent(connectionId)}&conda_env=${encodeURIComponent(condaEnv)}`
  )

  await ensureOk(response, 'Failed to get remote configuration')

  return response.json()
}

export async function acceptKnownHost(payload: KnownHostsAcceptRequest): Promise<{ ok: boolean }> {
  const response = await fetch(`${API_BASE}/known-hosts/accept`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  await ensureOk(response, 'Failed to accept host key')
  return response.json()
}

/**
 * Connect and start Remote Viewer in one step
 * This is a convenience function that starts Remote Viewer (which internally handles SSH connection)
 */
export async function quickStartRemoteViewer(
  config: SSHConnectionConfig
): Promise<RemoteSession> {
  if (!config.remoteRoot) {
    throw new Error('Remote storage root is required')
  }
  // Start Remote Viewer (which internally connects via SSH)
  const result: any = await startRemoteViewer(config)
  // Backend returns {ok: true, session: {...}}
  return result.session || result
}
