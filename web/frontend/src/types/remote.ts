/**
 * Remote Viewer Types
 * 
 * Type definitions for VSCode Remote-like architecture
 */

/**
 * SSH connection authentication methods
 */
export type AuthMethod = 'password' | 'key'

/**
 * Remote Viewer session status
 */
export type SessionStatus = 'connecting' | 'running' | 'stopping' | 'stopped' | 'error'

/**
 * SSH session status
 */
export type SSHStatus = 'connected' | 'disconnected' | 'connecting' | 'error'

/**
 * SSH connection configuration
 */
export interface SSHConnectionConfig {
  /** Remote host address */
  host: string
  /** SSH port (default: 22) */
  port: number
  /** SSH username */
  username: string
  /** Authentication method */
  authMethod: AuthMethod
  /** Password (if using password auth) */
  password?: string
  /** Private key path (if using key auth) */
  privateKeyPath?: string
  /** Passphrase for private key (optional) */
  passphrase?: string
  
  // Remote Viewer configuration
  /** Remote storage root directory */
  remoteRoot?: string
  /** Local port for SSH tunnel (optional, auto-assign if not provided) */
  localPort?: number
  /** Remote Viewer port (default: 23300) */
  remotePort?: number
  /** Conda environment name */
  condaEnv?: string
  
  // Save configuration
  /** Configuration name for saving */
  saveName?: string
  /** Whether to save password */
  savePassword?: boolean
}

/**
 * Saved connection configuration
 */
export interface SavedConnection {
  /** Unique ID */
  id: string
  /** Display name */
  name: string
  /** Remote host */
  host: string
  /** SSH port */
  port: number
  /** Username */
  username: string
  /** Authentication method */
  authMethod: AuthMethod
  /** Saved password (if user chose to save it) */
  password?: string
  /** Private key path */
  privateKeyPath?: string
  /** Conda environment name */
  condaEnv?: string
  /** Remote storage root */
  remoteRoot: string
  /** Local port preference */
  localPort?: number
  /** Remote port */
  remotePort?: number
  /** Creation timestamp */
  createdAt: number
}

export type SavedEntryKind = 'server' | 'connection'

export interface SavedServer {
  kind: 'server'
  id: string
  name: string
  host: string
  port: number
  username: string
  authMethod: AuthMethod
  password?: string
  privateKeyPath?: string
  passphrase?: string
  createdAt: number
}

export interface SavedConnectionProfile {
  kind: 'connection'
  id: string
  serverId: string
  name: string
  condaEnv?: string
  remoteRoot?: string
  localPort?: number
  remotePort?: number
  createdAt: number
}

export type SavedEntry = SavedServer | SavedConnectionProfile

/**
 * Active SSH session
 */
export interface SSHSession {
  /** Remote host */
  host: string
  /** SSH port */
  port: number
  /** Username */
  username: string
  /** Connection status */
  status: SSHStatus
  /** Connected timestamp */
  connectedAt: number
  /** Error message (if any) */
  error?: string
}

/**
 * Active Remote Viewer session
 */
export interface RemoteSession {
  /** Unique session ID */
  sessionId: string
  /** Remote host */
  host: string
  /** SSH port */
  sshPort: number
  /** SSH username */
  username: string
  /** Local port (for accessing viewer) */
  localPort: number
  /** Remote Viewer port */
  remotePort: number
  /** Remote storage root path */
  remoteRoot: string
  /** Session status */
  status: SessionStatus
  /** Started timestamp */
  startedAt: number
  /** Remote Viewer process ID */
  remotePid?: number
  /** Error message (if any) */
  error?: string
}

/**
 * Remote directory entry
 */
export interface RemoteFileEntry {
  /** File/directory name */
  name: string
  /** Full path */
  path: string
  /** Is directory */
  isDir: boolean
  /** File size (if file) */
  size?: number
  /** Modification time */
  mtime?: number
}

/**
 * API response wrapper
 */
export interface ApiResponse<T> {
  /** Success flag */
  ok: boolean
  /** Data payload */
  data?: T
  /** Error message */
  error?: string
  /** Error code */
  code?: string
}

/**
 * Connection test result
 */
export interface ConnectionTestResult {
  /** Test success */
  success: boolean
  /** Response time (ms) */
  responseTime?: number
  /** Error message */
  error?: string
  /** Remote OS info */
  osInfo?: string
  /** Remote Python version */
  pythonVersion?: string
}

/**
 * Conda environment info
 */
export interface CondaEnv {
  /** Environment name */
  name: string
  /** Environment type (conda or system) */
  type: 'conda' | 'system'
  /** Python version */
  pythonVersion: string
  /** Environment path */
  path: string
  /** Is default environment */
  isDefault: boolean
}

/**
 * Remote server configuration
 */
export interface RemoteConfig {
  /** Success flag */
  ok: boolean
  /** Conda environment name */
  condaEnv: string
  /** Python version */
  pythonVersion: string
  /** Runicorn version */
  runicornVersion: string
  /** Default storage root path */
  defaultStorageRoot: string
  /** Whether storage root exists */
  storageRootExists: boolean
  /** Suggested remote port */
  suggestedRemotePort: number
  /** Connection ID */
  connectionId: string
}

/**
 * SSH connection state (after Step 1)
 */
export interface SSHConnectionState {
  /** Connection ID */
  connectionId: string
  /** Original config */
  config: SSHConnectionConfig
  /** Available conda environments */
  condaEnvs?: CondaEnv[]
  /** Selected conda environment */
  selectedEnv?: string
  /** Remote config (after selecting environment) */
  remoteConfig?: RemoteConfig
}

export type HostKeyVerificationReason = 'unknown' | 'changed'

export interface HostKeyInfo {
  host: string
  port: number
  known_hosts_host: string
  key_type: string
  fingerprint_sha256: string
  public_key: string
  reason: HostKeyVerificationReason
  expected_fingerprint_sha256?: string
  expected_public_key?: string
}

export interface HostKeyConfirmationRequiredDetail {
  code: 'HOST_KEY_CONFIRMATION_REQUIRED'
  message: string
  host_key: HostKeyInfo
}

export interface KnownHostsAcceptRequest {
  host: string
  port: number
  key_type: string
  public_key: string
  fingerprint_sha256: string
}

export interface KnownHostsEntry {
  host: string
  port: number
  known_hosts_host: string
  key_type: string
  key_base64: string
  fingerprint_sha256: string
}

export interface KnownHostsRemoveRequest {
  host: string
  port: number
  key_type: string
}

export class ApiError<TDetail = unknown> extends Error {
  status: number
  detail?: TDetail

  constructor(status: number, message: string, detail?: TDetail) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    Object.setPrototypeOf(this, new.target.prototype)
  }
}
