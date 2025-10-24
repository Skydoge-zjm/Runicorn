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
  ApiResponse
} from '../types/remote'

const API_BASE = '/api/remote'

/**
 * Get local runicorn version
 */
export async function getLocalVersion(): Promise<string> {
  const response = await fetch('/api/health')
  if (!response.ok) {
    throw new Error('Failed to get local version')
  }
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

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to connect to remote server')
  }

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

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to disconnect')
  }
}

/**
 * List active SSH sessions
 */
export async function listSSHSessions(): Promise<SSHSession[]> {
  const response = await fetch(`${API_BASE}/sessions`)
  if (!response.ok) {
    throw new Error('Failed to list SSH sessions')
  }
  const data = await response.json()
  return data.sessions || data
}

/**
 * Start Remote Viewer on remote server
 */
export async function startRemoteViewer(
  config: SSHConnectionConfig
): Promise<RemoteSession> {
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
      remote_port: config.remotePort || 23300,
      conda_env: config.condaEnv
    })
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to start Remote Viewer')
  }

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

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to stop Remote Viewer')
  }
}

/**
 * List active Remote Viewer sessions
 */
export async function listRemoteSessions(): Promise<RemoteSession[]> {
  const response = await fetch(`${API_BASE}/viewer/sessions`)
  if (!response.ok) {
    throw new Error('Failed to list Remote Viewer sessions')
  }
  const data = await response.json()
  return data.sessions || data
}

/**
 * Get Remote Viewer session status
 */
export async function getSessionStatus(sessionId: string): Promise<RemoteSession> {
  const response = await fetch(`${API_BASE}/viewer/status/${sessionId}`)
  if (!response.ok) {
    throw new Error('Failed to get session status')
  }
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
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to list directory')
  }
  
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
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Connection test failed'
    }
  }
}

/**
 * List conda environments on remote server
 */
export async function listCondaEnvs(connectionId: string): Promise<any> {
  const response = await fetch(
    `${API_BASE}/conda-envs?connection_id=${encodeURIComponent(connectionId)}`
  )
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to list conda environments')
  }
  
  return response.json()
}

/**
 * Get remote server runicorn configuration
 */
export async function getRemoteConfig(connectionId: string, condaEnv: string = 'system'): Promise<any> {
  const response = await fetch(
    `${API_BASE}/config?connection_id=${encodeURIComponent(connectionId)}&conda_env=${encodeURIComponent(condaEnv)}`
  )
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to get remote configuration')
  }
  
  return response.json()
}

/**
 * Connect and start Remote Viewer in one step
 * This is a convenience function that starts Remote Viewer (which internally handles SSH connection)
 */
export async function quickStartRemoteViewer(
  config: SSHConnectionConfig
): Promise<RemoteSession> {
  // Start Remote Viewer (which internally connects via SSH)
  const result: any = await startRemoteViewer(config)
  // Backend returns {ok: true, session: {...}}
  return result.session || result
}
