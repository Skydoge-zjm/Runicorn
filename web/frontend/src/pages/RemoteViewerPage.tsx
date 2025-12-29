/**
 * Remote Viewer Page
 * 
 * Main page for managing Remote Viewer sessions (VSCode Remote-like architecture)
 */

import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Card,
  Space,
  Typography,
  Row,
  Col,
  Alert,
  Empty,
  message,
  Spin,
  Modal,
  Input,
  Table,
  Button,
  Popconfirm,
  Drawer,
  Collapse,
  List,
  Tag,
  Tooltip,
  Form,
  InputNumber,
  Radio,
  Checkbox,
  Divider
} from 'antd'
import {
  CloudServerOutlined,
  ThunderboltOutlined,
  SaveOutlined,
  SafetyCertificateOutlined,
  PlusOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

import RemoteSessionCard from '../components/remote/RemoteSessionCard'
import RemoteConfigCard from '../components/remote/RemoteConfigCard'
import CondaEnvSelector from '../components/remote/CondaEnvSelector'
import HostKeyModal from '../components/remote/HostKeyModal'
import DismissibleAlert from '../components/DismissibleAlert'
import FancyStatCard from '../components/fancy/FancyStatCard'
import { colorConfig } from '../config/animation_config'

import { useRemoteSessions } from '../hooks/useRemoteSessions'
import { useSavedConnections } from '../hooks/useSavedConnections'

import {
  connectRemote,
  listCondaEnvs,
  getRemoteConfig,
  startRemoteViewer,
  stopRemoteViewer,
  disconnectRemote,
  testConnection,
  acceptKnownHost,
  listKnownHosts,
  removeKnownHost
} from '../api/remote'

import { ApiError } from '../types/remote'
import type {
  HostKeyConfirmationRequiredDetail,
  HostKeyInfo,
  SSHConnectionConfig,
  SSHConnectionState,
  KnownHostsEntry,
  SavedConnectionProfile,
  SavedServer
} from '../types/remote'

const { Title, Paragraph, Text } = Typography

export default function RemoteViewerPage() {
  const { t } = useTranslation()
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
  const hostKeyDecisionResolverRef = useRef<((decision: 'confirm' | 'cancel') => void) | null>(null)
  const [knownHosts, setKnownHosts] = useState<KnownHostsEntry[]>([])
  const [knownHostsLoading, setKnownHostsLoading] = useState(false)
  const [securityDrawerOpen, setSecurityDrawerOpen] = useState(false)

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

  const serverCount = servers.length
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

  /**
   * Step 1: Connect to SSH server and list conda environments
   */
  const connectAndListEnvs = async (config: SSHConnectionConfig) => {
    setConnecting(true)
    
    try {
      const connectionId = `${config.username}@${config.host}:${config.port}`

      // 1. Connect via SSH
      await runWithHostKeyConfirmation(() => connectRemote(config), connectionId)
      
      setFetchingEnvs(true)
      
      // 3. List conda environments (show loading state)
      const envsResult = await listCondaEnvs(connectionId)
      
      // 4. Store connection state with environments
      setSSHConnection({
        connectionId,
        config,
        condaEnvs: envsResult.envs || [],
        selectedEnv: undefined,
        remoteConfig: undefined
      })
      
    } catch (error) {
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
  
  /**
   * Step 3: Save profile after config confirmation
   */
  const handleSaveProfile = async (profileName: string, remoteRoot: string, localPort?: number, remotePort?: number) => {
    if (!sshConnection || !sshConnection.remoteConfig) return
    if (!wizardServerId) return
    
    setStarting(true)
    try {
      const finalName = profileName?.trim() || `${sshConnection.selectedEnv || 'system'} - ${remoteRoot}`
      if (wizardEditProfileId) {
        await updateProfile(wizardEditProfileId, {
          name: finalName,
          condaEnv: sshConnection.selectedEnv,
          remoteRoot,
          localPort,
          remotePort
        })
      } else {
        await addProfile(wizardServerId, {
          name: finalName,
          condaEnv: sshConnection.selectedEnv,
          remoteRoot,
          localPort,
          remotePort
        })
      }

      // Disconnect SSH after saving config
      const { host, port, username } = sshConnection.config
      await disconnectRemote(host, port, username).catch(() => {})

      message.success(t('remote.message.configSaved'))
      
      setSSHConnection(null)
      setWizardOpen(false)
      setWizardServerId(null)
      setWizardEditProfileId(null)
      serverForm.resetFields()
      
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
    if (!sshConnection) return
    
    // Disconnect SSH
    const { host, port, username } = sshConnection.config
    await disconnectRemote(host, port, username)
    
    // Reset all connection-related states
    setSSHConnection(null)
    setFetchingEnvs(false)
    setFetchingConfig(false)
    setWizardOpen(false)
    setWizardServerId(null)
    setWizardEditProfileId(null)
    serverForm.resetFields()
    message.info(t('remote.message.cancelled'))
  }

  /**
   * Handle connection test
   */
  const handleTest = async (config: SSHConnectionConfig) => {
    const target = `${config.username}@${config.host}:${config.port}`
    try {
      const result = await runWithHostKeyConfirmation(() => testConnection(config), target)
      if (result.success) {
        message.success({
          content: (
            <div>
              <div>{t('remote.message.testSuccess')}</div>
              {result.pythonVersion && (
                <div style={{ fontSize: '12px', marginTop: 4 }}>
                  Python {result.pythonVersion}
                </div>
              )}
            </div>
          ),
          duration: 3
        })
      } else {
        throw new Error(result.error || 'Connection test failed')
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.message.testFailed'))
      throw error
    }
  }

  /**
   * Handle connect only (without starting viewer)
   */
  const openNewServerWizard = () => {
    setWizardOpen(true)
    setWizardServerId(null)
    setWizardEditProfileId(null)
    setSSHConnection(null)
    serverForm.resetFields()
  }

  const openNewProfileWizard = (serverId: string) => {
    setWizardOpen(true)
    setWizardServerId(serverId)
    setWizardEditProfileId(null)
    setSSHConnection(null)
    serverForm.resetFields()
  }

  const openEditProfileWizard = (serverId: string, profileId: string) => {
    setWizardOpen(true)
    setWizardServerId(serverId)
    setWizardEditProfileId(profileId)
    setSSHConnection(null)
    serverForm.resetFields()
  }

  const startWizardConnect = async () => {
    const values = await serverForm.validateFields()

    let server: SavedServer | null = null
    if (wizardServerId) {
      server = servers.find(s => s.id === wizardServerId) || null
    }

    const authMethod = (values.authMethod as 'password' | 'key') || server?.authMethod || 'password'

    const savePassword = Boolean(values.savePassword)

    const config: SSHConnectionConfig = {
      host: server?.host || values.host,
      port: server?.port || values.port || 22,
      username: server?.username || values.username,
      authMethod: authMethod,
      password: authMethod === 'password' ? (values.password || server?.password) : undefined,
      privateKeyPath: authMethod === 'key' ? (values.privateKeyPath || server?.privateKeyPath) : undefined,
      passphrase: authMethod === 'key' ? (values.passphrase || server?.passphrase) : undefined
    }

    if (!wizardServerId) {
      const serverId = await addServer({
        name: values.name,
        host: config.host,
        port: config.port,
        username: config.username,
        authMethod: config.authMethod,
        password: savePassword && config.authMethod === 'password' ? values.password : undefined,
        privateKeyPath: config.privateKeyPath,
        passphrase: config.passphrase
      })
      setWizardServerId(serverId)
    } else {
      if (savePassword && config.authMethod === 'password' && values.password) {
        await updateServer(wizardServerId, { password: values.password })
      }
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

    if (server.authMethod === 'password' && !server.password) {
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
        password: server.authMethod === 'password' ? (password || server.password) : undefined,
        privateKeyPath: server.authMethod === 'key' ? server.privateKeyPath : undefined,
        passphrase: server.authMethod === 'key' ? server.passphrase : undefined,
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
   * Handle disconnect
   */
  const handleDisconnect = async (session: any) => {
    try {
      await stopRemoteViewer(session.sessionId)
      await disconnectRemote(session.host, session.sshPort || 22, session.username || 'user')
      await refetchSessions()
      
      message.success(t('remote.message.disconnected'))
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.message.disconnectFailed'))
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

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      overflow: 'hidden',
      padding: 16,
    }}>
      {/* Page Header - fixed height */}
      <div style={{ flexShrink: 0, marginBottom: 16 }}>
        <Title level={2} style={{ marginBottom: 8 }}>
          <CloudServerOutlined /> {t('remote.title')}
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          {t('remote.subtitle')}
        </Paragraph>
      </div>

      {/* Architecture Introduction - fixed height */}
      <div style={{ flexShrink: 0 }}>
        <DismissibleAlert
          alertId="remote.intro"
          type="info"
          message={t('remote.help.architecture')}
          description={t('remote.help.advantages')}
          showIcon
          style={{ marginBottom: 16 }}
        />

        {/* Statistics */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <FancyStatCard
              title={t('remote.stats.activeSessions')}
              value={activeSessions.length}
              icon={<ThunderboltOutlined />}
              gradientColors={colorConfig.gradients.primary}
            />
          </Col>
          <Col span={8}>
            <FancyStatCard
              title={t('remote.stats.savedConfigs')}
              value={profileCount}
              icon={<SaveOutlined />}
              gradientColors={colorConfig.gradients.info}
            />
          </Col>
          <Col span={8}>
            <FancyStatCard
              title={t('remote.stats.connectedServers')}
              value={connectedServers}
              icon={<CloudServerOutlined />}
              gradientColors={colorConfig.gradients.success}
            />
          </Col>
        </Row>

        <Space style={{ marginBottom: 16 }}>
          <Button icon={<SafetyCertificateOutlined />} onClick={() => setSecurityDrawerOpen(true)}>
            {t('remote.security.advanced')}
          </Button>
        </Space>
      </div>

      {/* Main content: Two columns - fills remaining space */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        <Row gutter={24}>
        {/* Left Column: Saved Servers */}
        <Col xs={24} lg={12}>
          <Card
            title={t('remote.saved.title')}
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={openNewServerWizard}>
                {t('remote.saved.addServer')}
              </Button>
            }
            style={{ minHeight: 520 }}
          >
            {serverCount === 0 ? (
              <Empty description={t('remote.saved.noServers')} />
            ) : (
              <Collapse accordion>
                {servers.map(server => (
                  <Collapse.Panel
                    header={
                      <Space direction="vertical" size={0}>
                        <Text strong>{server.name}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          SSH {server.username}@{server.host}:{server.port}
                        </Text>
                      </Space>
                    }
                    key={server.id}
                    extra={
                      <Space>
                        <Button
                          size="small"
                          icon={<PlusOutlined />}
                          onClick={(e) => {
                            e.stopPropagation()
                            openNewProfileWizard(server.id)
                          }}
                        >
                          {t('remote.saved.addConnection')}
                        </Button>
                        <Popconfirm
                          title={t('remote.message.confirmDelete')}
                          onConfirm={() => deleteServer(server.id)}
                          okButtonProps={{ danger: true }}
                        >
                          <Button
                            size="small"
                            danger
                            onClick={(e) => e.stopPropagation()}
                          >
                            {t('remote.saved.delete')}
                          </Button>
                        </Popconfirm>
                      </Space>
                    }
                  >
                    <List
                      size="small"
                      dataSource={getProfilesForServer(server.id)}
                      locale={{ emptyText: t('remote.saved.noConnections') }}
                      renderItem={(profile) => (
                        <List.Item
                          style={{ paddingTop: '0.375rem', paddingBottom: '0.375rem' }}
                          actions={[
                            <Button
                              key="quickstart"
                              type="primary"
                              icon={<ThunderboltOutlined />}
                              size="small"
                              loading={quickStartingProfileId === profile.id}
                              disabled={quickStartingProfileId !== null && quickStartingProfileId !== profile.id}
                              onClick={() => handleQuickStartProfile(server.id, profile)}
                            >
                              {t('remote.saved.quickStart')}
                            </Button>,
                            <Button
                              key="edit"
                              size="small"
                              onClick={() => openEditProfileWizard(server.id, profile.id)}
                            >
                              {t('remote.saved.edit')}
                            </Button>,
                            <Popconfirm
                              key="delete"
                              title={t('remote.message.confirmDelete')}
                              onConfirm={() => deleteProfile(profile.id)}
                              okButtonProps={{ danger: true }}
                            >
                              <Button danger size="small">
                                {t('remote.saved.delete')}
                              </Button>
                            </Popconfirm>
                          ]}
                        >
                          <List.Item.Meta
                            title={
                              <Text
                                strong
                                style={{ lineHeight: '20px', display: 'block', marginBottom: 2 }}
                                ellipsis={{ tooltip: profile.name }}
                              >
                                {profile.name}
                              </Text>
                            }
                            description={
                              <div
                                style={{
                                  display: 'grid',
                                  gridTemplateColumns: 'clamp(6.5rem, 28%, 12rem) minmax(0, 1fr) auto',
                                  alignItems: 'center',
                                  gap: 6,
                                  minWidth: 0,
                                  lineHeight: '18px'
                                }}
                              >
                                <Tooltip title={profile.condaEnv || 'system'}>
                                  <Tag
                                    color="blue"
                                    style={{
                                      marginInlineEnd: 0,
                                      fontSize: 11,
                                      lineHeight: '16px',
                                      paddingInline: 6,
                                      maxWidth: '100%'
                                    }}
                                  >
                                    <Text
                                      style={{ maxWidth: '100%', display: 'inline-block', verticalAlign: 'top' }}
                                      ellipsis
                                    >
                                      {profile.condaEnv || 'system'}
                                    </Text>
                                  </Tag>
                                </Tooltip>

                                <Text
                                  type="secondary"
                                  code
                                  style={{
                                    fontSize: 11,
                                    lineHeight: '16px',
                                    minWidth: 0,
                                    display: 'inline-block'
                                  }}
                                  ellipsis={{ tooltip: profile.remoteRoot || '-' }}
                                >
                                  {profile.remoteRoot || '-'}
                                </Text>

                                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end', flexWrap: 'nowrap' }}>
                                  {(profile.localPort !== undefined || profile.remotePort !== undefined) && (
                                    <>
                                      <Tag
                                        style={{
                                          marginInlineEnd: 0,
                                          fontSize: 11,
                                          lineHeight: '16px',
                                          paddingInline: 6
                                        }}
                                      >
                                        L:{profile.localPort ?? 'auto'}
                                      </Tag>
                                      <Tag
                                        style={{
                                          marginInlineEnd: 0,
                                          fontSize: 11,
                                          lineHeight: '16px',
                                          paddingInline: 6
                                        }}
                                      >
                                        R:{profile.remotePort ?? 'auto'}
                                      </Tag>
                                    </>
                                  )}
                                </div>
                              </div>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  </Collapse.Panel>
                ))}
              </Collapse>
            )}
          </Card>
        </Col>

        {/* Right Column: Active Sessions */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                {t('remote.session.title')}
                {activeSessions.length > 0 && (
                  <Text type="secondary">({activeSessions.length})</Text>
                )}
              </Space>
            }
          >
            {activeSessions.length === 0 ? (
              <Empty
                description={
                  <Space direction="vertical">
                    <Text type="secondary">{t('remote.session.noActiveSessions')}</Text>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {t('remote.session.startNewConnection')}
                    </Text>
                  </Space>
                }
                style={{ margin: '40px 0' }}
              />
            ) : (
              activeSessions.map(session => (
                <RemoteSessionCard
                  key={session.sessionId}
                  session={session}
                  onStop={handleStopSession}
                  onDisconnect={handleDisconnect}
                />
              ))
            )}
          </Card>
        </Col>
      </Row>
      </div>

      <Drawer
        title={wizardTitle}
        open={wizardOpen}
        onClose={() => {
          if (sshConnection) {
            void handleCancelConfig()
            return
          }
          setWizardOpen(false)
          setWizardServerId(null)
          setWizardEditProfileId(null)
          setSSHConnection(null)
          serverForm.resetFields()
        }}
        width={560}
        destroyOnClose
      >
        <div style={{ minHeight: 520 }}>
          {!sshConnection ? (
            <>
              {wizardServerId && wizardServer ? (
                <Alert
                  type="info"
                  showIcon
                  message={`${wizardServer.username}@${wizardServer.host}:${wizardServer.port}`}
                  style={{ marginBottom: 16 }}
                />
              ) : null}
              <Form
                form={serverForm}
                layout="vertical"
                initialValues={{
                  port: 22,
                  authMethod: wizardServer?.authMethod || 'password',
                  host: wizardServer?.host,
                  username: wizardServer?.username,
                  name: wizardServer?.name,
                  privateKeyPath: wizardServer?.privateKeyPath,
                  passphrase: wizardServer?.passphrase,
                  savePassword: false
                }}
              >
                {!wizardServerId && (
                  <Form.Item label={t('remote.form.saveName')} name="name">
                    <Input placeholder={t('remote.form.saveNamePlaceholder')} />
                  </Form.Item>
                )}

                {!wizardServerId && (
                  <>
                    <Form.Item
                      label={t('remote.form.host')}
                      name="host"
                      rules={[{ required: true, message: t('remote.form.required') }]}
                    >
                      <Input placeholder={t('remote.form.hostPlaceholder')} />
                    </Form.Item>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item label={t('remote.form.port')} name="port">
                          <InputNumber min={1} max={65535} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          label={t('remote.form.username')}
                          name="username"
                          rules={[{ required: true, message: t('remote.form.required') }]}
                        >
                          <Input placeholder={t('remote.form.usernamePlaceholder')} />
                        </Form.Item>
                      </Col>
                    </Row>
                  </>
                )}

                <Form.Item label={t('remote.form.authMethod')} name="authMethod">
                  <Radio.Group>
                    <Radio value="password">{t('remote.form.passwordAuth')}</Radio>
                    <Radio value="key">{t('remote.form.keyAuth')}</Radio>
                  </Radio.Group>
                </Form.Item>

                <Form.Item noStyle shouldUpdate>
                  {() => {
                    const method = serverForm.getFieldValue('authMethod') as 'password' | 'key'
                    return method === 'password' ? (
                      <>
                        <Form.Item
                          label={t('remote.form.password')}
                          name="password"
                          rules={wizardServerId && wizardServer?.authMethod === 'password' && wizardServer.password ? [] : [{ required: true, message: t('remote.form.required') }]}
                        >
                          <Input.Password />
                        </Form.Item>

                        {(!wizardServerId || (wizardServerId && wizardServer && wizardServer.authMethod === 'password' && !wizardServer.password)) && (
                          <Form.Item name="savePassword" valuePropName="checked">
                            <Checkbox>{t('remote.form.savePassword')}</Checkbox>
                          </Form.Item>
                        )}
                      </>
                    ) : (
                      <>
                        <Form.Item
                          label={t('remote.form.privateKey')}
                          name="privateKeyPath"
                          rules={[{ required: true, message: t('remote.form.required') }]}
                        >
                          <Input placeholder={t('remote.form.privateKeyPlaceholder')} />
                        </Form.Item>
                        <Form.Item label={t('remote.form.passphrase')} name="passphrase">
                          <Input.Password />
                        </Form.Item>
                      </>
                    )
                  }}
                </Form.Item>

                <Divider />
                <Space>
                  <Button type="primary" loading={connecting} onClick={() => void startWizardConnect()}>
                    {t('remote.form.connectButton')}
                  </Button>
                  <Button
                    onClick={() => {
                      setWizardOpen(false)
                      setWizardServerId(null)
                      setWizardEditProfileId(null)
                      setSSHConnection(null)
                      serverForm.resetFields()
                    }}
                  >
                    {t('remote.form.cancel')}
                  </Button>
                </Space>
              </Form>
            </>
          ) : sshConnection.remoteConfig ? (
            <Spin spinning={fetchingConfig} tip={t('remote.config.fetchingConfig')}>
              <RemoteConfigCard
                config={sshConnection.remoteConfig}
                sshConfig={{
                  ...sshConnection.config,
                  saveName: wizardProfile?.name,
                  remoteRoot: wizardProfile?.remoteRoot,
                  localPort: wizardProfile?.localPort,
                  remotePort: wizardProfile?.remotePort
                }}
                onConfirm={handleSaveProfile}
                onCancel={handleCancelConfig}
                loading={starting}
              />
            </Spin>
          ) : (
            <Spin spinning={fetchingEnvs} tip={t('remote.env.fetching')}>
              <CondaEnvSelector
                envs={sshConnection.condaEnvs || []}
                connectionId={sshConnection.connectionId}
                initialEnv={wizardProfile?.condaEnv}
                onSelect={handleSelectEnvironment}
                onCancel={handleCancelConfig}
                loading={fetchingConfig}
              />
            </Spin>
          )}
        </div>
      </Drawer>

      <Drawer
        title={t('remote.knownHosts.title')}
        open={securityDrawerOpen}
        onClose={() => setSecurityDrawerOpen(false)}
        width={860}
      >
        <Space style={{ marginBottom: 12 }}>
          <Button onClick={() => void loadKnownHosts()} loading={knownHostsLoading}>
            {t('remote.knownHosts.refresh')}
          </Button>
        </Space>
        <Table
          dataSource={knownHosts}
          loading={knownHostsLoading}
          rowKey={record => `${record.known_hosts_host}-${record.key_type}`}
          pagination={false}
          locale={{ emptyText: t('remote.knownHosts.empty') }}
          columns={[
            {
              title: t('remote.form.host'),
              dataIndex: 'host',
              key: 'host',
              render: (text: string, record: KnownHostsEntry) => (
                <Text code>{record.known_hosts_host || `${text}:${record.port}`}</Text>
              )
            },
            {
              title: t('remote.hostKey.keyType'),
              dataIndex: 'key_type',
              key: 'key_type',
              render: (text: string) => <Text code>{text}</Text>
            },
            {
              title: t('remote.hostKey.fingerprint'),
              dataIndex: 'fingerprint_sha256',
              key: 'fingerprint_sha256',
              render: (text: string) => (
                <Text code copyable>
                  {text}
                </Text>
              )
            },
            {
              title: t('remote.knownHosts.actions'),
              key: 'actions',
              render: (_: unknown, record: KnownHostsEntry) => (
                <Popconfirm
                  title={t('remote.knownHosts.removeConfirm')}
                  onConfirm={() => void handleRemoveKnownHost(record)}
                  okButtonProps={{ danger: true }}
                >
                  <Button danger size="small">
                    {t('remote.knownHosts.remove')}
                  </Button>
                </Popconfirm>
              )
            }
          ]}
        />
      </Drawer>

      {/* Password Input Dialog */}
      <Modal
        title={t('remote.form.enterPassword')}
        open={passwordDialogVisible}
        onOk={handlePasswordSubmit}
        onCancel={handlePasswordCancel}
        okText={t('remote.form.connectButton')}
        cancelText={t('remote.form.cancel')}
        confirmLoading={starting}
        centered
        width={400}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Text>
            {t('remote.form.connectionTo')}: <Text strong>{passwordDialogProfile?.name}</Text>
          </Text>
          <Text type="secondary">
            {passwordDialogServer?.username}@{passwordDialogServer?.host}
          </Text>
          <Input.Password
            placeholder={t('remote.form.password')}
            value={tempPassword}
            onChange={e => setTempPassword(e.target.value)}
            onPressEnter={handlePasswordSubmit}
            autoFocus
            size="large"
          />
        </Space>
      </Modal>

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
