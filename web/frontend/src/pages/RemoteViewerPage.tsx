/**
 * Remote Viewer Page
 * 
 * Main page for managing Remote Viewer sessions (VSCode Remote-like architecture)
 */

import React, { useEffect, useRef, useState } from 'react'
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
  Popconfirm
} from 'antd'
import {
  CloudServerOutlined,
  ThunderboltOutlined,
  SaveOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

import SSHConnectionForm from '../components/remote/SSHConnectionForm'
import RemoteSessionCard from '../components/remote/RemoteSessionCard'
import SavedConnectionsList from '../components/remote/SavedConnectionsList'
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
  SavedConnection,
  SSHConnectionConfig,
  SSHConnectionState,
  KnownHostsEntry
} from '../types/remote'

const { Title, Paragraph, Text } = Typography

export default function RemoteViewerPage() {
  const { t } = useTranslation()
  const [connecting, setConnecting] = useState(false)
  const [sshConnected, setSSHConnected] = useState(false)
  const [fetchingEnvs, setFetchingEnvs] = useState(false)
  const [fetchingConfig, setFetchingConfig] = useState(false)
  const [starting, setStarting] = useState(false)
  
  // Step 1: SSH connection, Step 2: Select env, Step 3: Config confirmation
  const [sshConnection, setSSHConnection] = useState<SSHConnectionState | null>(null)
  const [savedConnectionId, setSavedConnectionId] = useState<string | null>(null)
  
  // Password input dialog
  const [passwordDialogVisible, setPasswordDialogVisible] = useState(false)
  const [passwordDialogConnection, setPasswordDialogConnection] = useState<SavedConnection | null>(null)
  const [passwordDialogAction, setPasswordDialogAction] = useState<'connect' | 'quickstart'>('connect')
  const [tempPassword, setTempPassword] = useState('')

  const [hostKeyModalOpen, setHostKeyModalOpen] = useState(false)
  const [hostKeyModalLoading, setHostKeyModalLoading] = useState(false)
  const [hostKeyModalTarget, setHostKeyModalTarget] = useState<string | undefined>(undefined)
  const [hostKeyModalHostKey, setHostKeyModalHostKey] = useState<HostKeyInfo | undefined>(undefined)
  const hostKeyDecisionResolverRef = useRef<((decision: 'confirm' | 'cancel') => void) | null>(null)
  const [knownHosts, setKnownHosts] = useState<KnownHostsEntry[]>([])
  const [knownHostsLoading, setKnownHostsLoading] = useState(false)

  // Hooks
  const { sessions, refetch: refetchSessions } = useRemoteSessions()
  const {
    connections,
    saveConnection,
    updateConnection,
    deleteConnection
  } = useSavedConnections()

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
    void loadKnownHosts()
  }, [])

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
  const handleConnect = async (config: SSHConnectionConfig) => {
    setConnecting(true)
    setSSHConnected(false)
    
    try {
      const connectionId = `${config.username}@${config.host}:${config.port}`

      // 1. Connect via SSH
      await runWithHostKeyConfirmation(() => connectRemote(config), connectionId)
      
      // 2. SSH connected, show success and start fetching environments
      setConnecting(false)
      setSSHConnected(true)
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
      
      // Save connection if requested (will be updated with conda_env later)
      if (config.saveName) {
        // Save password only if user chose to save it
        const shouldSavePassword = config.savePassword && config.authMethod === 'password'
        const configToSave = shouldSavePassword
          ? config 
          : { ...config, password: undefined }
        
        console.log('Saving connection:', {
          saveName: config.saveName,
          savePassword: config.savePassword,
          authMethod: config.authMethod,
          hasPassword: !!config.password,
          shouldSavePassword
        })
        
        const connId = await saveConnection(configToSave)
        setSavedConnectionId(connId)
        message.success(t('remote.message.configSaved'))
      }
      
    } catch (error) {
      setSSHConnected(false)
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
        selectedEnv: envName,
        remoteConfig
      })
      
      // Update saved connection with conda env if it was saved
      if (savedConnectionId) {
        updateConnection(savedConnectionId, {
          condaEnv: envName
        })
      }
      
      // Don't show success message here, only show message when viewer starts
      
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.config.fetchFailed'))
    } finally {
      setFetchingConfig(false)
    }
  }
  
  /**
   * Step 3: Start Remote Viewer after config confirmation
   */
  const handleStartViewer = async (remoteRoot: string, localPort?: number) => {
    if (!sshConnection || !sshConnection.remoteConfig) return
    
    setStarting(true)
    try {
      const config: SSHConnectionConfig = {
        ...sshConnection.config,
        remoteRoot,
        localPort,
        remotePort: sshConnection.remoteConfig.suggestedRemotePort,
        condaEnv: sshConnection.selectedEnv
      }

      const target = `${config.username}@${config.host}:${config.port}`
      
      // Update saved connection with complete info before starting
      if (savedConnectionId) {
        await updateConnection(savedConnectionId, {
          remoteRoot,
          localPort,
          remotePort: sshConnection.remoteConfig.suggestedRemotePort
        })
      }
      
      await runWithHostKeyConfirmation(() => startRemoteViewer(config), target)
      await refetchSessions()
      message.success(t('remote.message.viewerStarted'))
      
      // Reset to initial state
      setSSHConnection(null)
      setSavedConnectionId(null)
      setSSHConnected(false)
      
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.message.viewerStartFailed'))
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
    setSSHConnected(false)
    setFetchingEnvs(false)
    setFetchingConfig(false)
    setSavedConnectionId(null)
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
  const handleConnectOnly = async (conn: SavedConnection) => {
    // If password auth and no password saved, show dialog
    if (conn.authMethod === 'password' && !conn.password) {
      setPasswordDialogConnection(conn)
      setPasswordDialogAction('connect')
      setPasswordDialogVisible(true)
      return
    }
    
    await executeConnect(conn, conn.password)
  }
  
  /**
   * Execute connection with provided password
   */
  const executeConnect = async (conn: SavedConnection, password?: string) => {
    setConnecting(true)
    setSSHConnected(false)
    
    try {
      const config: SSHConnectionConfig = {
        host: conn.host,
        port: conn.port,
        username: conn.username,
        authMethod: conn.authMethod,
        password: password || conn.password,  // Use provided password or saved one
        privateKeyPath: conn.privateKeyPath,
        remoteRoot: conn.remoteRoot || '',
        localPort: conn.localPort,
        remotePort: conn.remotePort
      }

      const connectionId = `${config.username}@${config.host}:${config.port}`
      
      // Connect via SSH
      await runWithHostKeyConfirmation(() => connectRemote(config), connectionId)
      setConnecting(false)
      setSSHConnected(true)
      message.success(t('remote.message.connectSuccess'))
      setFetchingEnvs(true)
      
      // List conda environments
      const envsResult = await listCondaEnvs(connectionId)
      
      // Store connection state
      setSSHConnection({
        connectionId,
        config,
        condaEnvs: envsResult.envs || [],
        selectedEnv: conn.condaEnv,
        remoteConfig: undefined
      })
      
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.message.connectFailed'))
      setSSHConnected(false)
      await disconnectRemote(conn.host, conn.port, conn.username).catch(() => {})
      throw error  // Re-throw to handle in dialog
    } finally {
      setConnecting(false)
      setFetchingEnvs(false)
    }
  }

  /**
   * Handle quick start from saved connection
   */
  const handleQuickStart = async (conn: SavedConnection) => {
    // Check if we have all required info for quick start
    if (!conn.condaEnv || !conn.remoteRoot) {
      message.warning(t('remote.message.incompleteConfig'))
      // TODO: Show pre-filled connection form
      return
    }
    
    // If password auth and no password saved, show dialog
    if (conn.authMethod === 'password' && !conn.password) {
      setPasswordDialogConnection(conn)
      setPasswordDialogAction('quickstart')
      setPasswordDialogVisible(true)
      return
    }
    
    await executeQuickStart(conn, conn.password)
  }
  
  /**
   * Execute quick start with provided password
   */
  const executeQuickStart = async (conn: SavedConnection, password?: string) => {
    setConnecting(true)
    setSSHConnected(false)
    setFetchingEnvs(true)
    setFetchingConfig(true)
    
    try {
      const config: SSHConnectionConfig = {
        host: conn.host,
        port: conn.port,
        username: conn.username,
        authMethod: conn.authMethod,
        password: password || conn.password,  // Use provided password or saved one
        privateKeyPath: conn.privateKeyPath,
        remoteRoot: conn.remoteRoot,
        localPort: conn.localPort,
        remotePort: conn.remotePort
      }

      const target = `${config.username}@${config.host}:${config.port}`
      
      // 1. Connect via SSH
      await runWithHostKeyConfirmation(() => connectRemote(config), target)
      setConnecting(false)
      setSSHConnected(true)
      message.success(t('remote.message.connectSuccess'))
      
      // 2. Get remote config for saved environment
      const connectionId = `${config.username}@${config.host}:${config.port}`
      const remoteConfig = await getRemoteConfig(connectionId, conn.condaEnv)
      
      // 3. Start Remote Viewer directly
      const viewerConfig: SSHConnectionConfig = {
        ...config,
        remoteRoot: conn.remoteRoot,
        remotePort: remoteConfig.suggestedRemotePort,
        condaEnv: conn.condaEnv
      }
      
      await runWithHostKeyConfirmation(() => startRemoteViewer(viewerConfig), target)
      await refetchSessions()
      message.success(t('remote.message.viewerStarted'))
      
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.message.viewerStartFailed'))
      setSSHConnected(false)
      await disconnectRemote(conn.host, conn.port, conn.username).catch(() => {})
      throw error  // Re-throw to handle in dialog
    } finally {
      setConnecting(false)
      setFetchingEnvs(false)
      setFetchingConfig(false)
    }
  }

  /**
   * Handle session stop
   */
  const handleStopSession = async (session: any) => {
    try {
      await stopRemoteViewer(session.sessionId)
      await refetchSessions()
      
      // Only reset connection state if not currently configuring a new connection
      // This allows users to have multiple sessions and stop one without affecting others
      if (!sshConnection) {
        setSSHConnected(false)
        setSavedConnectionId(null)
      }
      
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
      
      // Only reset connection state if not currently configuring a new connection
      // This allows users to have multiple sessions and disconnect one without affecting others
      if (!sshConnection) {
        setSSHConnected(false)
        setSavedConnectionId(null)
      }
      
      message.success(t('remote.message.disconnected'))
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.message.disconnectFailed'))
      throw error
    }
  }

  const activeSessions = sessions.filter(s => s.status !== 'stopped')
  const connectedServers = new Set(sessions.map(s => s.host)).size

  /**
   * Handle password dialog submit
   */
  const handlePasswordSubmit = async () => {
    if (!passwordDialogConnection || !tempPassword) {
      message.warning(t('remote.form.password') + ' ' + t('remote.form.required'))
      return
    }
    
    try {
      if (passwordDialogAction === 'connect') {
        await executeConnect(passwordDialogConnection, tempPassword)
      } else {
        await executeQuickStart(passwordDialogConnection, tempPassword)
      }
      
      // Success - close dialog
      setPasswordDialogVisible(false)
      setTempPassword('')
      setPasswordDialogConnection(null)
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
    setPasswordDialogConnection(null)
  }

  return (
    <div>
      {/* Page Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <CloudServerOutlined /> {t('remote.title')}
        </Title>
        <Paragraph type="secondary">
          {t('remote.subtitle')}
        </Paragraph>
      </div>

      {/* Architecture Introduction */}
      <DismissibleAlert
        alertId="remote.intro"
        type="info"
        message={t('remote.help.architecture')}
        description={t('remote.help.advantages')}
        showIcon
        style={{ marginBottom: 24 }}
      />

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
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
            value={connections.length}
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

      <Row gutter={24}>
        {/* Left Column: Connection Form / Env Selector / Config Confirmation */}
        <Col xs={24} lg={12}>
          {sshConnection ? (
            // Step 2 or Step 3 (after SSH connected)
            sshConnection.remoteConfig ? (
              // Step 3: Config Confirmation (after env selected)
              <Spin spinning={fetchingConfig} tip={t('remote.config.fetchingConfig')}>
                <RemoteConfigCard
                  config={sshConnection.remoteConfig}
                  sshConfig={sshConnection.config}
                  onConfirm={handleStartViewer}
                  onCancel={handleCancelConfig}
                  loading={starting}
                />
              </Spin>
            ) : (
              // Step 2: Conda Environment Selection (after SSH connected)
              <Spin spinning={fetchingEnvs} tip={t('remote.env.fetching')}>
                <CondaEnvSelector
                  envs={sshConnection.condaEnvs || []}
                  connectionId={sshConnection.connectionId}
                  onSelect={handleSelectEnvironment}
                  onCancel={handleCancelConfig}
                  loading={fetchingConfig}
                />
              </Spin>
            )
          ) : (
            // Step 1: SSH Connection Form
            <>
              <Card title={t('remote.form.title')} style={{ marginBottom: 24 }}>
                {sshConnected && fetchingEnvs ? (
                  // Show success state while fetching environments
                  <Space direction="vertical" style={{ width: '100%' }} size="large">
                    <Alert
                      message={t('remote.message.connectSuccess')}
                      description={t('remote.env.fetching')}
                      type="success"
                      showIcon
                      icon={<CheckCircleOutlined />}
                    />
                    <div style={{ textAlign: 'center', padding: '24px 0' }}>
                      <Spin size="large" tip={t('remote.env.detectingEnvironments')} />
                    </div>
                  </Space>
                ) : (
                  <SSHConnectionForm
                    onSubmit={handleConnect}
                    onTest={handleTest}
                    loading={connecting}
                  />
                )}
              </Card>

              {!sshConnected && !fetchingEnvs && (
                <SavedConnectionsList
                  connections={connections}
                  onQuickStart={handleQuickStart}
                  onConnect={handleConnectOnly}
                  onDelete={deleteConnection}
                  loading={connecting}
                />
              )}
            </>
          )}
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

      {/* Known Hosts Management */}
      <Card
        title={t('remote.knownHosts.title')}
        style={{ marginTop: 24 }}
        extra={
          <Button onClick={() => loadKnownHosts()} loading={knownHostsLoading}>
            {t('remote.knownHosts.refresh')}
          </Button>
        }
      >
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
                  onConfirm={() => handleRemoveKnownHost(record)}
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
      </Card>

      {/* Help Section */}
      <Card title={t('remote.help.title')} style={{ marginTop: 24 }}>
        <Space direction="vertical">
          <Text>{t('remote.help.step1')}</Text>
          <Text>{t('remote.help.step2')}</Text>
          <Text>{t('remote.help.step3')}</Text>
          <Text>{t('remote.help.step4')}</Text>
          <Text>{t('remote.help.step5')}</Text>
          <Text>{t('remote.help.step6')}</Text>
        </Space>
      </Card>

      {/* Password Input Dialog */}
      <Modal
        title={t('remote.form.enterPassword')}
        open={passwordDialogVisible}
        onOk={handlePasswordSubmit}
        onCancel={handlePasswordCancel}
        okText={t('remote.form.connectButton')}
        cancelText={t('remote.form.cancel')}
        confirmLoading={connecting}
        centered
        width={400}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Text>
            {t('remote.form.connectionTo')}: <Text strong>{passwordDialogConnection?.name}</Text>
          </Text>
          <Text type="secondary">
            {passwordDialogConnection?.username}@{passwordDialogConnection?.host}
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
