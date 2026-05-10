/**
 * Remote Viewer Page
 * 
 * Main page for managing Remote Viewer sessions (VSCode Remote-like architecture)
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Card,
  Row,
  Col,
  Empty,
  App,
  Form,
} from 'antd'
import { useTranslation } from 'react-i18next'

import RemoteSessionCard from '../components/remote/RemoteSessionCard'
import HostKeyModal from '../components/remote/HostKeyModal'
import KnownHostsDrawer from './remote-viewer/KnownHostsDrawer'
import PasswordPromptModal from './remote-viewer/PasswordPromptModal'
import RemoteViewerOverview from './remote-viewer/RemoteViewerOverview'
import RemoteWizardModal from './remote-viewer/RemoteWizardModal'
import SavedServersPanel from './remote-viewer/SavedServersPanel'

import { useRemoteSessions } from '../hooks/useRemoteSessions'
import { useSavedConnections } from '../hooks/useSavedConnections'

import {
  connectRemote,
  listCondaEnvs,
  getRemoteConfig,
  listRemoteStorageCandidates,
  startRemoteViewer,
  stopRemoteViewer,
  disconnectRemote,
  acceptKnownHost,
  listKnownHosts,
  removeKnownHost
} from '../api/remote'

import { ApiError } from '../types/remote'
import type {
  HostKeyConfirmationRequiredDetail,
  HostKeyInfo,
  RemoteStorageCandidate,
  SSHConnectionConfig,
  SSHConnectionState,
  KnownHostsEntry,
  SavedConnectionProfile,
  SavedServer
} from '../types/remote'

export default function RemoteViewerPage() {
  const { t } = useTranslation()
  const { message } = App.useApp()
  const [connecting, setConnecting] = useState(false)
  const [fetchingEnvs, setFetchingEnvs] = useState(false)
  const [fetchingConfig, setFetchingConfig] = useState(false)
  const [starting, setStarting] = useState(false)
  const [quickStartingProfileId, setQuickStartingProfileId] = useState<string | null>(null)
  
  // Step 1: SSH connection, Step 2: Select env, Step 3: Config confirmation
  const [sshConnection, setSSHConnection] = useState<SSHConnectionState | null>(null)
  const [wizardOpen, setWizardOpen] = useState(false)
  const [wizardServerId, setWizardServerId] = useState<string | null>(null)
  const [wizardEditProfileId, setWizardEditProfileId] = useState<string | null>(null)
  const [serverForm] = Form.useForm()
  
  // Password input dialog
  const [passwordDialogVisible, setPasswordDialogVisible] = useState(false)
  const [passwordDialogServer, setPasswordDialogServer] = useState<SavedServer | null>(null)
  const [passwordDialogProfile, setPasswordDialogProfile] = useState<SavedConnectionProfile | null>(null)
  const [tempPassword, setTempPassword] = useState('')

  const [hostKeyModalOpen, setHostKeyModalOpen] = useState(false)
  const [hostKeyModalLoading, setHostKeyModalLoading] = useState(false)
  const [hostKeyModalTarget, setHostKeyModalTarget] = useState<string | undefined>(undefined)
  const [hostKeyModalHostKey, setHostKeyModalHostKey] = useState<HostKeyInfo | undefined>(undefined)
  const [storageCandidates, setStorageCandidates] = useState<RemoteStorageCandidate[]>([])
  const [fetchingStorageCandidates, setFetchingStorageCandidates] = useState(false)
  const [storageCandidatesRequested, setStorageCandidatesRequested] = useState(false)
  const hostKeyDecisionResolverRef = useRef<((decision: 'confirm' | 'cancel') => void) | null>(null)
  const [knownHosts, setKnownHosts] = useState<KnownHostsEntry[]>([])
  const [knownHostsLoading, setKnownHostsLoading] = useState(false)
  const [securityDrawerOpen, setSecurityDrawerOpen] = useState(false)
  const [wizardProgress, setWizardProgress] = useState<string | null>(null)
  const progressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wizardFlowIdRef = useRef(0)
  const pendingWizardConnectionRef = useRef<Pick<SSHConnectionConfig, 'host' | 'port' | 'username'> | null>(null)

  // Hooks
  const { sessions, refetch: refetchSessions } = useRemoteSessions()
  const {
    servers,
    getProfilesForServer,
    addServer,
    updateServer,
    deleteServer,
    addProfile,
    updateProfile,
    deleteProfile
  } = useSavedConnections()

  const profileCount = useMemo(() => {
    return servers.reduce((acc, srv) => acc + getProfilesForServer(srv.id).length, 0)
  }, [getProfilesForServer, servers])

  const activeSessions = sessions.filter(s => s.status !== 'stopped')
  const connectedServers = new Set(sessions.map(s => s.host)).size

  const isHostKeyConfirmationRequiredError = (
    error: unknown
  ): error is ApiError<HostKeyConfirmationRequiredDetail> => {
    if (!(error instanceof ApiError)) {
      return false
    }

    if (error.status !== 409) {
      return false
    }

    const detail = error.detail
    if (!detail || typeof detail !== 'object') {
      return false
    }

    return (detail as { code?: unknown }).code === 'HOST_KEY_CONFIRMATION_REQUIRED'
  }

  const waitForHostKeyDecision = async (): Promise<'confirm' | 'cancel'> => {
    return new Promise((resolve) => {
      hostKeyDecisionResolverRef.current = resolve
    })
  }

  const handleHostKeyConfirm = () => {
    hostKeyDecisionResolverRef.current?.('confirm')
    hostKeyDecisionResolverRef.current = null
  }

  const handleHostKeyCancel = () => {
    hostKeyDecisionResolverRef.current?.('cancel')
    hostKeyDecisionResolverRef.current = null
    setHostKeyModalOpen(false)
    setHostKeyModalTarget(undefined)
    setHostKeyModalHostKey(undefined)
  }

  const loadKnownHosts = async () => {
    setKnownHostsLoading(true)
    try {
      const entries = await listKnownHosts()
      setKnownHosts(entries)
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.knownHosts.loadFailed'))
    } finally {
      setKnownHostsLoading(false)
    }
  }

  const handleRemoveKnownHost = async (entry: KnownHostsEntry) => {
    setKnownHostsLoading(true)
    try {
      await removeKnownHost({
        host: entry.host,
        port: entry.port,
        key_type: entry.key_type
      })
      message.success(t('remote.knownHosts.removeSuccess'))
      await loadKnownHosts()
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.knownHosts.removeFailed'))
    } finally {
      setKnownHostsLoading(false)
    }
  }

  useEffect(() => {
    if (securityDrawerOpen) {
      void loadKnownHosts()
    }
  }, [securityDrawerOpen])

  const runWithHostKeyConfirmation = async <T,>(
    action: () => Promise<T>,
    target: string
  ): Promise<T> => {
    while (true) {
      try {
        return await action()
      } catch (error) {
        if (!isHostKeyConfirmationRequiredError(error)) {
          throw error
        }

        const detail = error.detail
        const hostKey = detail?.host_key
        if (!hostKey) {
          throw error
        }

        setHostKeyModalTarget(target)
        setHostKeyModalHostKey(hostKey)
        setHostKeyModalOpen(true)

        const decision = await waitForHostKeyDecision()
        if (decision !== 'confirm') {
          setHostKeyModalOpen(false)
          setHostKeyModalTarget(undefined)
          setHostKeyModalHostKey(undefined)
          throw new Error(t('remote.message.cancelled'))
        }

        setHostKeyModalLoading(true)
        try {
          await acceptKnownHost({
            host: hostKey.host,
            port: hostKey.port,
            key_type: hostKey.key_type,
            public_key: hostKey.public_key,
            fingerprint_sha256: hostKey.fingerprint_sha256
          })
          if (securityDrawerOpen) {
            await loadKnownHosts()
          }
        } finally {
          setHostKeyModalLoading(false)
          setHostKeyModalOpen(false)
          setHostKeyModalTarget(undefined)
          setHostKeyModalHostKey(undefined)
        }
      }
    }
  }

  const clearWizardProgressTimer = () => {
    if (progressTimerRef.current) {
      clearTimeout(progressTimerRef.current)
      progressTimerRef.current = null
    }
  }

  const invalidateWizardFlow = () => {
    wizardFlowIdRef.current += 1
    clearWizardProgressTimer()
    setWizardProgress(null)
    return wizardFlowIdRef.current
  }

  const cleanupPendingWizardConnection = async () => {
    const pending = pendingWizardConnectionRef.current
    pendingWizardConnectionRef.current = null
    if (!pending) {
      return
    }
    await disconnectRemote(pending.host, pending.port, pending.username).catch(() => {})
  }

  /**
   * Step 1: Connect to SSH server and list conda environments
   */
  const connectAndListEnvs = async (config: SSHConnectionConfig) => {
    const flowId = invalidateWizardFlow()
    pendingWizardConnectionRef.current = {
      host: config.host,
      port: config.port,
      username: config.username,
    }
    setConnecting(true)
    setWizardProgress(t('remote.wizard.progress_connecting'))
    
    try {
      const connectionId = `${config.username}@${config.host}:${config.port}`

      // Simulate sub-step: show "authenticating" after a short delay during the single API call
      progressTimerRef.current = setTimeout(() => {
        setWizardProgress(t('remote.wizard.progress_authenticating'))
      }, 1500)

      // 1. Connect via SSH (includes auth)
      await runWithHostKeyConfirmation(() => connectRemote(config), connectionId)
      clearWizardProgressTimer()
      if (wizardFlowIdRef.current !== flowId) {
        await cleanupPendingWizardConnection()
        return
      }
      
      // 2. Finding conda
      setWizardProgress(t('remote.wizard.progress_finding_conda'))
      setFetchingEnvs(true)

      progressTimerRef.current = setTimeout(() => {
        setWizardProgress(t('remote.wizard.progress_listing_envs'))
      }, 2000)
      
      // 3. List conda environments
      const envsResult = await listCondaEnvs(connectionId)
      clearWizardProgressTimer()
      if (wizardFlowIdRef.current !== flowId) {
        await cleanupPendingWizardConnection()
        return
      }
      
      setWizardProgress(null)
      pendingWizardConnectionRef.current = null

      // 4. Store connection state with environments
      setSSHConnection({
        connectionId,
        config,
        condaEnvs: envsResult.envs || [],
        selectedEnv: undefined,
        remoteConfig: undefined
      })
      
    } catch (error) {
      clearWizardProgressTimer()
      pendingWizardConnectionRef.current = null
      setWizardProgress(null)
      // Clean up on error
      await disconnectRemote(config.host, config.port, config.username).catch(() => {})
      throw error
    } finally {
      setConnecting(false)
      setFetchingEnvs(false)
    }
  }
  
  /**
   * Step 2: Select conda environment and get configuration
   */
  const handleSelectEnvironment = async (envName: string) => {
    if (!sshConnection) return
    
    setFetchingConfig(true)
    setStorageCandidates([])
    setStorageCandidatesRequested(false)
    try {
      // Get remote config for selected environment
      const remoteConfig = await getRemoteConfig(sshConnection.connectionId, envName)
      
      // Update connection state with selected env and config
      setSSHConnection({
        ...sshConnection,
        config: { ...sshConnection.config, condaEnv: envName },
        selectedEnv: envName,
        remoteConfig
      })
      
      // Don't show success message here, only show message when viewer starts
      
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.config.fetchFailed'))
    } finally {
      setFetchingConfig(false)
    }
  }

  const handleDetectStorageCandidates = async (scanRoot: string, maxDepth: number) => {
    if (!sshConnection || !sshConnection.selectedEnv) return

    setFetchingStorageCandidates(true)
    setStorageCandidatesRequested(true)
    try {
      const detectedStorageCandidates = await listRemoteStorageCandidates(
        sshConnection.connectionId,
        sshConnection.selectedEnv,
        scanRoot,
        maxDepth,
      )
      setStorageCandidates(detectedStorageCandidates)
    } catch (error) {
      setStorageCandidates([])
      message.warning(
        error instanceof Error
          ? error.message
          : t('remote.config.detectFailed'),
      )
    } finally {
      setFetchingStorageCandidates(false)
    }
  }
  
  /**
   * Step 3: Save profile after config confirmation, then connect and start Viewer
   */
  const handleSaveProfile = async (profileName: string, remoteRoot: string, localPort?: number, remotePort?: number) => {
    if (!sshConnection || !sshConnection.remoteConfig) return
    if (!wizardServerId) return
    
    setStarting(true)
    try {
      const finalName = profileName?.trim() || `${sshConnection.selectedEnv || 'system'} - ${remoteRoot}`
      const profileData = {
        name: finalName,
        condaEnv: sshConnection.selectedEnv,
        remoteRoot,
        localPort,
        remotePort
      }
      let savedProfileId: string
      if (wizardEditProfileId) {
        await updateProfile(wizardEditProfileId, profileData)
        savedProfileId = wizardEditProfileId
      } else {
        savedProfileId = await addProfile(wizardServerId, profileData)
      }

      // Disconnect SSH after saving config
      const { host, port, username } = sshConnection.config
      await disconnectRemote(host, port, username).catch(() => {})

      message.success(t('remote.message.configSaved'))
      
      const serverIdToStart = wizardServerId
      setSSHConnection(null)
      setStorageCandidates([])
      setStorageCandidatesRequested(false)
      setWizardOpen(false)
      setWizardServerId(null)
      setWizardEditProfileId(null)
      serverForm.resetFields()

      // Fulfill wizard promise: connect and start Viewer for the saved profile
      const server = servers.find(s => s.id === serverIdToStart)
      const profile = wizardEditProfileId
        ? { ...wizardProfile, ...profileData } as SavedConnectionProfile
        : { ...profileData, id: savedProfileId, serverId: serverIdToStart } as SavedConnectionProfile
      if (server && profile.condaEnv && profile.remoteRoot) {
        if (server.authMethod === 'password' && !server.password && !server.hasSavedPassword) {
          setPasswordDialogServer(server)
          setPasswordDialogProfile(profile as SavedConnectionProfile)
          setPasswordDialogVisible(true)
        } else {
          await executeQuickStart(server, profile as SavedConnectionProfile, server.password)
        }
      }
      
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.message.saveFailed'))
    } finally {
      setStarting(false)
    }
  }
  
  /**
   * Cancel config confirmation (disconnect SSH)
   */
  const handleCancelConfig = async () => {
    invalidateWizardFlow()
    await cleanupPendingWizardConnection()
    if (!sshConnection) return
    
    // Disconnect SSH
    const { host, port, username } = sshConnection.config
    await disconnectRemote(host, port, username)
    
    // Reset all connection-related states
    setSSHConnection(null)
    setStorageCandidates([])
    setStorageCandidatesRequested(false)
    setFetchingEnvs(false)
    setFetchingConfig(false)
    setFetchingStorageCandidates(false)
    setWizardOpen(false)
    setWizardServerId(null)
    setWizardEditProfileId(null)
    serverForm.resetFields()
    message.info(t('remote.message.cancelled'))
  }

  /**
   * Handle connect only (without starting viewer)
   */
  const openNewServerWizard = () => {
    invalidateWizardFlow()
    setWizardOpen(true)
    setWizardServerId(null)
    setWizardEditProfileId(null)
    setSSHConnection(null)
    setStorageCandidates([])
    setStorageCandidatesRequested(false)
    serverForm.resetFields()
  }

  const openNewProfileWizard = (serverId: string) => {
    invalidateWizardFlow()
    setWizardOpen(true)
    setWizardServerId(serverId)
    setWizardEditProfileId(null)
    setSSHConnection(null)
    setStorageCandidates([])
    setStorageCandidatesRequested(false)
    serverForm.resetFields()
  }

  const openEditProfileWizard = (serverId: string, profileId: string) => {
    invalidateWizardFlow()
    setWizardOpen(true)
    setWizardServerId(serverId)
    setWizardEditProfileId(profileId)
    setSSHConnection(null)
    setStorageCandidates([])
    setStorageCandidatesRequested(false)
    serverForm.resetFields()
  }

  const startWizardConnect = async () => {
    const values = await serverForm.validateFields()

    let server: SavedServer | null = null
    if (wizardServerId) {
      server = servers.find(s => s.id === wizardServerId) || null
    }

    const authMethod = (values.authMethod as 'password' | 'key') || server?.authMethod || 'password'

    const savePassword = authMethod === 'password' ? Boolean(values.savePassword) : false
    const savePassphrase = authMethod === 'key' ? Boolean(values.savePassphrase) : false

    const config: SSHConnectionConfig = {
      host: server?.host || values.host,
      port: server?.port || values.port || 22,
      username: server?.username || values.username,
      authMethod: authMethod,
      savedServerId: wizardServerId || undefined,
      password: authMethod === 'password' ? (values.password || undefined) : undefined,
      privateKeyPath: authMethod === 'key' ? (values.privateKeyPath || server?.privateKeyPath) : undefined,
      passphrase: authMethod === 'key' ? (values.passphrase || undefined) : undefined
    }

    if (!wizardServerId) {
      const serverId = await addServer({
        name: values.name,
        host: config.host,
        port: config.port,
        username: config.username,
        authMethod: config.authMethod,
        password: savePassword && config.authMethod === 'password' ? values.password : undefined,
        privateKeyPath: config.authMethod === 'key' ? config.privateKeyPath : undefined,
        passphrase: savePassphrase && config.authMethod === 'key' ? values.passphrase : undefined,
        hasSavedPassword: savePassword,
        hasSavedPassphrase: savePassphrase,
        hasSavedPrivateKey: config.authMethod === 'key' && Boolean(config.privateKeyPath),
      })
      setWizardServerId(serverId)
    } else {
      const updates: Partial<SavedServer> = { authMethod: config.authMethod }

      if (config.authMethod === 'password') {
        updates.password = savePassword ? (values.password || undefined) : null
        updates.hasSavedPassword = savePassword
        updates.privateKeyPath = null
        updates.passphrase = null
        updates.hasSavedPrivateKey = false
        updates.hasSavedPassphrase = false
      } else {
        updates.password = null
        updates.hasSavedPassword = false
        updates.privateKeyPath = config.privateKeyPath || null
        updates.hasSavedPrivateKey = Boolean(config.privateKeyPath)
        updates.passphrase = savePassphrase ? (values.passphrase || undefined) : null
        updates.hasSavedPassphrase = savePassphrase
      }

      await updateServer(wizardServerId, updates)
    }

    await connectAndListEnvs(config)
  }

  const handleQuickStartProfile = async (serverId: string, profile: SavedConnectionProfile) => {
    const server = servers.find(s => s.id === serverId)
    if (!server) return

    setQuickStartingProfileId(profile.id)

    if (!profile.condaEnv || !profile.remoteRoot) {
      message.warning(t('remote.message.incompleteConfig'))
      openEditProfileWizard(serverId, profile.id)
      setQuickStartingProfileId(null)
      return
    }

    if (server.authMethod === 'password' && !server.password && !server.hasSavedPassword) {
      setPasswordDialogServer(server)
      setPasswordDialogProfile(profile)
      setPasswordDialogVisible(true)
      return
    }

    await executeQuickStart(server, profile, server.password)
  }

  const executeQuickStart = async (server: SavedServer, profile: SavedConnectionProfile, password?: string) => {
    const msgKey = 'remote.quickStart'
    setStarting(true)
    message.loading({ content: t('remote.message.quickStartStarting'), key: msgKey, duration: 0 })
    try {
      const usedLocalPorts = new Set(activeSessions.map(s => s.localPort))
      const usedRemotePorts = new Set(
        activeSessions
          .filter(s => s.host === server.host && s.sshPort === server.port)
          .map(s => s.remotePort)
      )

      const config: SSHConnectionConfig = {
        host: server.host,
        port: server.port,
        username: server.username,
        authMethod: server.authMethod,
        savedServerId: server.id,
        password: server.authMethod === 'password' ? (password || server.password) : undefined,
        privateKeyPath: server.authMethod === 'key' ? server.privateKeyPath : undefined,
        passphrase: server.authMethod === 'key' ? (password ? undefined : server.passphrase) : undefined,
        condaEnv: profile.condaEnv,
        remoteRoot: profile.remoteRoot,
        localPort: profile.localPort,
        remotePort: profile.remotePort
      }

      // Avoid port conflicts when multiple sessions run on the same server.
      // If the saved port is already in use, let backend auto-assign a free one.
      if (config.localPort !== undefined && usedLocalPorts.has(config.localPort)) {
        config.localPort = undefined
      }
      if (config.remotePort !== undefined && usedRemotePorts.has(config.remotePort)) {
        config.remotePort = undefined
      }

      // Extra safety: remote viewer port must not clash with SSH port on the same host.
      if (config.remotePort !== undefined && config.remotePort === server.port) {
        config.remotePort = undefined
      }

      const target = `${config.username}@${config.host}:${config.port}`
      await runWithHostKeyConfirmation(() => startRemoteViewer(config), target)
      await refetchSessions()
      message.success({ content: t('remote.message.viewerStarted'), key: msgKey })
    } catch (error) {
      message.error({
        content: error instanceof Error ? error.message : t('remote.message.viewerStartFailed'),
        key: msgKey
      })
      throw error
    } finally {
      setStarting(false)
      setQuickStartingProfileId(null)
    }
  }

  /**
   * Handle session stop
   */
  const handleStopSession = async (session: any) => {
    try {
      await stopRemoteViewer(session.sessionId)
      await refetchSessions()
      
      message.success(t('remote.message.viewerStopped'))
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.message.viewerStopFailed'))
      throw error
    }
  }


  /**
   * Handle password dialog submit
   */
  const handlePasswordSubmit = async () => {
    if (!passwordDialogServer || !passwordDialogProfile || !tempPassword) {
      message.warning(t('remote.form.password') + ' ' + t('remote.form.required'))
      return
    }
    
    try {
      await executeQuickStart(passwordDialogServer, passwordDialogProfile, tempPassword)
      
      // Success - close dialog
      setPasswordDialogVisible(false)
      setTempPassword('')
      setPasswordDialogServer(null)
      setPasswordDialogProfile(null)
    } catch (error) {
      // Error already shown in execute functions
      // Keep dialog open for retry
    }
  }
  
  /**
   * Handle password dialog cancel
   */
  const handlePasswordCancel = () => {
    setPasswordDialogVisible(false)
    setTempPassword('')
    setPasswordDialogServer(null)
    setPasswordDialogProfile(null)
    setQuickStartingProfileId(null)
  }

  const wizardTitle = useMemo(() => {
    if (!wizardServerId) {
      return t('remote.saved.addServer')
    }
    if (wizardEditProfileId) {
      return t('remote.saved.edit')
    }
    return t('remote.saved.addConnection')
  }, [t, wizardEditProfileId, wizardServerId])

  const wizardServer = useMemo(() => {
    if (!wizardServerId) return null
    return servers.find(s => s.id === wizardServerId) || null
  }, [servers, wizardServerId])

  const wizardProfile = useMemo(() => {
    if (!wizardServerId || !wizardEditProfileId) return null
    return getProfilesForServer(wizardServerId).find(p => p.id === wizardEditProfileId) || null
  }, [getProfilesForServer, wizardEditProfileId, wizardServerId])

  const closeWizardForm = () => {
    invalidateWizardFlow()
    void cleanupPendingWizardConnection()
    setWizardOpen(false)
    setWizardServerId(null)
    setWizardEditProfileId(null)
    setSSHConnection(null)
    setStorageCandidates([])
    setStorageCandidatesRequested(false)
    serverForm.resetFields()
  }

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      overflow: 'hidden',
      padding: 16,
    }}>
      <RemoteViewerOverview
        activeSessionCount={activeSessions.length}
        connectedServers={connectedServers}
        profileCount={profileCount}
        onOpenSecurity={() => setSecurityDrawerOpen(true)}
      />

      {/* Main content: Two columns - fills remaining space */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden' }}>
        <Row gutter={24}>
          <Col xs={24} lg={12}>
            <SavedServersPanel
              servers={servers}
              getProfilesForServer={getProfilesForServer}
              quickStartingProfileId={quickStartingProfileId}
              onAddServer={openNewServerWizard}
              onAddConnection={openNewProfileWizard}
              onQuickStartProfile={handleQuickStartProfile}
              onEditProfile={openEditProfileWizard}
              onDeleteServer={deleteServer}
              onDeleteProfile={deleteProfile}
            />
          </Col>

        {/* Right Column: Active Sessions */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <span>
                {t('remote.session.title')}
                {activeSessions.length > 0 && (
                  <span style={{ color: 'rgba(0,0,0,0.45)', marginLeft: 8 }}>({activeSessions.length})</span>
                )}
              </span>
            }
          >
            {activeSessions.length === 0 ? (
              <Empty
                description={
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <span style={{ color: 'rgba(0,0,0,0.45)' }}>{t('remote.session.noActiveSessions')}</span>
                    <span style={{ color: 'rgba(0,0,0,0.45)', fontSize: 12 }}>
                      {t('remote.session.startNewConnection')}
                    </span>
                  </div>
                }
                style={{ margin: '40px 0' }}
              />
            ) : (
              activeSessions.map(session => (
                <RemoteSessionCard
                  key={session.sessionId}
                  session={session}
                  onStop={handleStopSession}
                />
              ))
            )}
          </Card>
        </Col>
      </Row>
      </div>

      <RemoteWizardModal
        title={wizardTitle}
        open={wizardOpen}
        onCancel={() => {
          if (sshConnection) {
            void handleCancelConfig()
            return
          }
          closeWizardForm()
        }}
        connecting={connecting}
        fetchingConfig={fetchingConfig}
        fetchingEnvs={fetchingEnvs}
        fetchingStorageCandidates={fetchingStorageCandidates}
        loading={starting}
        profile={wizardProfile}
        progressText={wizardProgress}
        server={wizardServer}
        serverForm={serverForm}
        sshConnection={sshConnection}
        storageCandidates={storageCandidates}
        storageCandidatesRequested={storageCandidatesRequested}
        onCloseForm={closeWizardForm}
        onConfirmConfig={handleSaveProfile}
        onConnect={() => void startWizardConnect()}
        onDetectStorageCandidates={(scanRoot, maxDepth) => void handleDetectStorageCandidates(scanRoot, maxDepth)}
        onSelectEnvironment={(envName) => void handleSelectEnvironment(envName)}
      />

      <KnownHostsDrawer
        open={securityDrawerOpen}
        knownHosts={knownHosts}
        loading={knownHostsLoading}
        onClose={() => setSecurityDrawerOpen(false)}
        onRefresh={() => void loadKnownHosts()}
        onRemove={(entry) => void handleRemoveKnownHost(entry)}
      />

      <PasswordPromptModal
        open={passwordDialogVisible}
        loading={starting}
        profile={passwordDialogProfile}
        server={passwordDialogServer}
        password={tempPassword}
        onChangePassword={setTempPassword}
        onSubmit={() => void handlePasswordSubmit()}
        onCancel={handlePasswordCancel}
      />

      <HostKeyModal
        open={hostKeyModalOpen}
        loading={hostKeyModalLoading}
        target={hostKeyModalTarget}
        hostKey={hostKeyModalHostKey}
        onConfirm={handleHostKeyConfirm}
        onCancel={handleHostKeyCancel}
      />
    </div>
  )
}
