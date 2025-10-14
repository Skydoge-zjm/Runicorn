import React, { useState, useEffect, useCallback } from 'react'
import { 
  Card, 
  Space, 
  Typography, 
  Tag, 
  message, 
  Alert,
  Button,
  Input,
  InputNumber,
  Switch,
  Spin,
  Empty,
  Badge,
  Descriptions,
  Tooltip,
  Radio
} from 'antd'
import {  
  CloudServerOutlined, 
  CloudSyncOutlined,
  LinkOutlined,
  FolderOpenOutlined,
  FileOutlined,
  SyncOutlined,
  UpOutlined,
  ReloadOutlined,
  StopOutlined,
  DisconnectOutlined,
  DatabaseOutlined,
  ThunderboltOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

import SSHConfigForm, { type SSHConfig } from '../components/remote/SSHConfigForm'

import {
  // Unified SSH APIs
  unifiedConnect,
  unifiedDisconnect,
  unifiedStatus,
  unifiedConfigureMode,
  unifiedDeactivateMode,
  unifiedListdir,
  
  // Smart mode APIs
  getRemoteStatus,
  remoteSyncMetadata,
  verifyRemoteConnection,
  
  // Mirror mode APIs
  sshMirrorStart,
  sshMirrorStop,
  sshMirrorList,
  
  // SSH connection config APIs
  getSavedSSHConnections,
  saveSSHConnection,
  deleteSSHConnection,
  getSSHConnectionDetails,
} from '../api'

const { Title, Text } = Typography

interface DirectoryItem {
  name: string
  path: string
  type: 'dir' | 'file' | 'unknown'
  size: number
  mtime: number
}

interface MirrorTask {
  id: string
  remote_root: string
  local_root: string
  interval: number
  stats: {
    copied_files?: number
    appended_bytes?: number
    scans?: number
  }
  alive: boolean
}

export default function UnifiedRemotePage() {
  const { t } = useTranslation()
  
  // ===== Sync Mode Selection =====
  const [syncMode, setSyncMode] = useState<'smart' | 'mirror'>('smart')
  
  // ===== SSH Configuration (Shared) =====
  const [sshConfig, setSshConfig] = useState<SSHConfig>({
    host: '',
    port: 22,
    username: '',
    authMethod: 'key',
    password: '',
    privateKey: '',
    privateKeyPath: '',
    passphrase: '',
  })
  
  // ===== Saved Connections State =====
  const [savedConnections, setSavedConnections] = useState<any[]>([])
  const [rememberConnection, setRememberConnection] = useState(false)
  const [rememberPassword, setRememberPassword] = useState(false)
  const [connectionName, setConnectionName] = useState('')
  
  // ===== Unified Connection State =====
  const [connecting, setConnecting] = useState(false)
  const [sshConnected, setSshConnected] = useState(false)
  const [connectionInfo, setConnectionInfo] = useState<any>(null)
  const [connectionId, setConnectionId] = useState<string>('')
  
  // ===== Directory Browser State =====
  const [currentPath, setCurrentPath] = useState<string>('~')
  const [items, setItems] = useState<DirectoryItem[]>([])
  const [listing, setListing] = useState(false)
  const [selectedPath, setSelectedPath] = useState<string>('')
  
  // ===== Smart Mode State =====
  const [smartActive, setSmartActive] = useState(false)
  const [autoSync, setAutoSync] = useState(true)
  const [syncInterval, setSyncInterval] = useState(10)
  const [syncing, setSyncing] = useState(false)
  const [syncProgress, setSyncProgress] = useState<any>(null)
  
  // ===== Mirror Mode State =====
  const [mirrorInterval, setMirrorInterval] = useState(2)
  const [mirrors, setMirrors] = useState<MirrorTask[]>([])
  
  // ===== Unified Connection Status Polling =====
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await unifiedStatus()
        setSshConnected(status.connected)
        setConnectionInfo(status.connected ? status : null)
        setConnectionId(status.connection_id || '')
        
        // Update mode-specific states
        if (status.modes?.smart?.active) {
          setSmartActive(true)
        }
        if (status.modes?.mirror?.tasks) {
          setMirrors(status.modes.mirror.tasks || [])
        }
      } catch (error) {
        // Ignore polling errors
      }
    }
    
    checkStatus()
    const interval = setInterval(checkStatus, 2000)
    
    return () => clearInterval(interval)
  }, [])
  
  // ===== Load Saved Connections =====
  useEffect(() => {
    const loadConnections = async () => {
      try {
        const result = await getSavedSSHConnections()
        setSavedConnections(result.connections || [])
      } catch (error) {
        // Ignore errors
      }
    }
    loadConnections()
  }, [])
  
  // ===== Smart Mode: Sync Progress Polling =====
  useEffect(() => {
    if (!smartActive || !syncing) return
    
    const interval = setInterval(async () => {
      try {
        const status = await getRemoteStatus()
        setSyncProgress(status.sync_progress)
        
        // Auto-stop syncing indicator
        if (status.sync_progress?.status === 'completed') {
          setSyncing(false)
          message.success(t('remote_storage.sync.complete'))
        }
        
        if (status.sync_progress?.status === 'failed') {
          setSyncing(false)
          message.error(t('remote_storage.sync.failed'))
        }
      } catch (error) {
        // Ignore polling errors
      }
    }, 2000)
    
    return () => clearInterval(interval)
  }, [smartActive, syncing])
  
  // ===== Mirror Mode: Task Polling =====
  useEffect(() => {
    if (!sshConnected || syncMode !== 'mirror') return
    
    const loadMirrors = async () => {
      try {
        const res = await sshMirrorList()
        setMirrors(res.mirrors || [])
      } catch (error) {
        // Ignore polling errors
      }
    }
    
    loadMirrors()
    const interval = setInterval(loadMirrors, 3000)
    
    return () => clearInterval(interval)
  }, [sshConnected, syncMode])
  
  // ===== SSH Connection Handler =====
  const handleConnect = async (configOverride?: SSHConfig, skipSave?: boolean) => {
    // Use provided config or fall back to state
    const config = configOverride || sshConfig
    
    if (!config.host || !config.username) {
      message.error(t('remote.msg.fill_host_user'))
      return
    }
    
    setConnecting(true)
    
    try {
      const result = await unifiedConnect({
        host: config.host,
        port: config.port,
        username: config.username,
        password: config.authMethod === 'password' ? config.password : undefined,
        private_key: config.authMethod === 'key' ? config.privateKey : undefined,
        private_key_path: config.authMethod === 'key' ? config.privateKeyPath : undefined,
        passphrase: config.passphrase,
        use_agent: config.authMethod === 'agent',
      })
      
      if (result.ok) {
        message.success(t('remote.msg.ssh_connected'))
        setSshConnected(true)
        setConnectionInfo(result)
        setConnectionId(result.connection_id)
        
        // Save connection if requested (skip if it's a one-click connect)
        if (rememberConnection && !skipSave) {
          try {
            await saveSSHConnection({
              host: config.host,
              port: config.port,
              username: config.username,
              name: connectionName || `${config.username}@${config.host}`,
              auth_method: config.authMethod,
              private_key_path: config.privateKeyPath,
              remember_password: rememberPassword,
              password: rememberPassword ? config.password : undefined,
              private_key: rememberPassword ? config.privateKey : undefined,
              passphrase: rememberPassword ? config.passphrase : undefined,
            })
            // Reload saved connections
            const result = await getSavedSSHConnections()
            setSavedConnections(result.connections || [])
          } catch (error: any) {
            console.error('Failed to save connection:', error)
          }
        }
        
        // Auto list home directory
        await listRemoteDir('~')
      }
    } catch (error: any) {
      message.error(`${t('remote.msg.connect_failed')}: ${error.message}`)
    } finally {
      setConnecting(false)
    }
  }
  
  const handleDisconnect = async () => {
    try {
      await unifiedDisconnect()
      message.success(t('remote_storage.msg.disconnect_success'))
      resetConnectionState()
    } catch (error: any) {
      message.error(`${t('remote_storage.msg.disconnect_failed')}: ${error.message}`)
    }
  }
  
  const resetConnectionState = () => {
    setSshConnected(false)
    setConnectionInfo(null)
    setConnectionId('')
    setSmartActive(false)
    setSyncing(false)
    setSyncProgress(null)
    setItems([])
    setSelectedPath('')
  }
  
  // ===== Load Saved Connection =====
  const loadSavedConnection = async (conn: any) => {
    try {
      // Get full connection details including password
      const result = await getSSHConnectionDetails(conn.key)
      
      if (!result.ok || !result.connection) {
        message.error(t('remote_storage.msg.load_failed'))
        return
      }
      
      const fullConn = result.connection
      
      // Build config object
      const newConfig: SSHConfig = {
        host: fullConn.host || '',
        port: fullConn.port || 22,
        username: fullConn.username || '',
        authMethod: fullConn.auth_method || (fullConn.password ? 'password' : 'key'),
        password: fullConn.password || '',
        privateKey: fullConn.private_key || '',
        privateKeyPath: fullConn.private_key_path || '',
        passphrase: fullConn.passphrase || '',
      }
      
      // Fill in the form
      setSshConfig(newConfig)
      setConnectionName(fullConn.name || '')
      setRememberConnection(true)
      setRememberPassword(fullConn.remember_password || false)
      
      // If password is saved, auto-connect
      if (fullConn.remember_password && (fullConn.password || fullConn.private_key)) {
        message.info(t('remote_storage.msg.auto_connecting'))
        // Direct connect with the config object, skip saving since it's already saved
        handleConnect(newConfig, true)
      }
    } catch (error: any) {
      message.error(`${t('remote_storage.msg.load_failed')}: ${error.message}`)
    }
  }
  
  const deleteSavedConnection = async (key: string) => {
    try {
      await deleteSSHConnection(key)
      const result = await getSavedSSHConnections()
      setSavedConnections(result.connections || [])
      message.success(t('remote_storage.msg.connection_deleted'))
    } catch (error: any) {
      message.error(`${t('remote_storage.msg.delete_failed')}: ${error.message}`)
    }
  }
  
  // ===== Directory Browser =====
  const listRemoteDir = async (path: string) => {
    if (!sshConnected) return
    
    setListing(true)
    
    try {
      const result = await unifiedListdir(path)
      setItems(result.items || [])
      setCurrentPath(result.current_path || path)
    } catch (error: any) {
      message.error(`${t('remote.msg.dir_failed')}: ${error.message}`)
    } finally {
      setListing(false)
    }
  }
  
  const handlePathUp = () => {
    const path = currentPath
    
    if (path === '~' || path === '/') return
    
    if (path.startsWith('~')) {
      const rest = path.slice(1)
      const segs = rest.split('/').filter(Boolean)
      if (segs.length <= 1) {
        listRemoteDir('~')
        return
      }
      const parent = '~/' + segs.slice(0, -1).join('/')
      listRemoteDir(parent)
      return
    }
    
    const parts = path.split('/').filter(Boolean)
    parts.pop()
    const parent = '/' + parts.join('/')
    listRemoteDir(parent || '/')
  }
  
  // ===== Sync Handlers =====
  const handleStartSync = async () => {
    if (!sshConnected || !selectedPath) {
      message.warning(t('remote.msg.need_path'))
      return
    }
    
    if (syncMode === 'smart') {
      // Smart mode: Configure and start metadata sync
      try {
        const result = await unifiedConfigureMode({
          mode: 'smart',
          remote_root: selectedPath,
          auto_sync: autoSync,
          sync_interval_minutes: syncInterval,
        })
        
        if (result.ok) {
          setSmartActive(true)
          setSyncing(true)
          
          // Start metadata sync
          await remoteSyncMetadata()
          message.success(t('remote_storage.msg.smart_configured'))
        }
      } catch (error: any) {
        message.error(`${t('remote_storage.msg.config_failed')}: ${error.message}`)
      }
    } else {
      // Mirror mode: Start full sync
    try {
      await sshMirrorStart({
          session_id: connectionId,
          remote_root: selectedPath,
          interval: mirrorInterval,
      })
      message.success(t('remote.msg.started'))
      
      // Notify runs page to refresh
      try {
        window.dispatchEvent(new Event('runicorn:refresh'))
      } catch (error) {
        // Ignore
      }
    } catch (error: any) {
      message.error(`${t('remote.msg.start_failed')}: ${error.message}`)
      }
    }
  }
  
  const handleStopMirror = async (taskId: string) => {
    try {
      await sshMirrorStop(taskId)
      message.info(t('remote.tasks.stop'))
    } catch (error) {
      // Ignore errors
    }
  }
  
  const handleManualSync = async () => {
    setSyncing(true)
    
    try {
      await remoteSyncMetadata()
      message.info(t('remote_storage.msg.sync_started'))
    } catch (error: any) {
      message.error(`${t('remote_storage.sync.failed')}: ${error.message}`)
      setSyncing(false)
    }
  }
  
  const handleVerify = async () => {
    try {
      const result = await verifyRemoteConnection()
      
      if (result.connected) {
        message.success(t('remote_storage.msg.verify_ok'))
      } else {
        message.warning(t('remote_storage.msg.verify_failed'))
      }
    } catch (error: any) {
      message.error(`${t('remote_storage.status.verify')}: ${error.message}`)
    }
  }
  
  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: 24 }}>
      <Title level={2}>
        <CloudServerOutlined /> {t('unified_remote.title')}
      </Title>
      
      <Text type="secondary">
        {t('unified_remote.subtitle')}
      </Text>
      
      <Space direction="vertical" style={{ width: '100%', marginTop: 24 }} size="large">
        {/* SSH Connection Status */}
        {sshConnected && (
          <Alert
            type="success"
            icon={<LinkOutlined />}
            message={t('unified_remote.connection_active')}
            description={
              <Space>
                <Text>{connectionInfo?.username}@{connectionInfo?.host}:{connectionInfo?.port}</Text>
                <Tag color="green">{t('unified_remote.connected')}</Tag>
              </Space>
            }
            action={
              <Button danger size="small" onClick={handleDisconnect}>
                {t('remote.disconnect')}
              </Button>
            }
          />
        )}
        
        {/* SSH Configuration */}
        {!sshConnected && (
          <Card title={t('unified_remote.ssh_config_title')}>
            {/* Saved Connections */}
            {savedConnections.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <Text strong>{t('remote_storage.saved_connections')}:</Text>
                <Space direction="vertical" style={{ width: '100%', marginTop: 8 }}>
                  {savedConnections.map((conn) => (
                    <div 
                      key={conn.key} 
            style={{
                        padding: '8px 12px', 
                        border: '1px solid #f0f0f0', 
                        borderRadius: 4,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
              cursor: 'pointer',
                        transition: 'all 0.2s',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = '#1890ff'
                        e.currentTarget.style.background = '#f0f8ff'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = '#f0f0f0'
                        e.currentTarget.style.background = 'transparent'
                      }}
                      onClick={() => loadSavedConnection(conn)}
                    >
                      <Space>
                        <LinkOutlined />
                        <Text>{conn.name || conn.key}</Text>
                        {(conn.has_password || conn.has_private_key) ? (
                          <Tooltip title={t('remote_storage.one_click_connect')}>
                            <Tag color="green" icon={<ThunderboltOutlined />}>
                              {t('remote_storage.password_saved')}
                            </Tag>
                          </Tooltip>
                        ) : (
                          <Tooltip title={t('remote_storage.need_password')}>
                            <Tag>{t('remote_storage.no_password')}</Tag>
                          </Tooltip>
                        )}
                      </Space>
                      <Button 
                        size="small" 
                        danger 
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteSavedConnection(conn.key)
                        }}
                      >
                        {t('remote_storage.actions.delete')}
                      </Button>
                    </div>
                  ))}
                </Space>
              </div>
            )}
            
            <SSHConfigForm 
              config={sshConfig} 
              onChange={setSshConfig}
              disabled={sshConnected}
            />
            
            {/* Remember Options */}
            <Space direction="vertical" style={{ width: '100%', marginTop: 16 }}>
              <Space>
                <Switch
                  checked={rememberConnection}
                  onChange={setRememberConnection}
                />
                <Text>{t('remote_storage.remember_connection')}</Text>
              </Space>
              
              {rememberConnection && (
                <>
                  <Input
                    placeholder={t('remote_storage.connection_name_placeholder')}
                    value={connectionName}
                    onChange={(e) => setConnectionName(e.target.value)}
                    style={{ marginBottom: 8 }}
                  />
              <Space>
                    <Switch
                      checked={rememberPassword}
                      onChange={setRememberPassword}
                      disabled={!rememberConnection}
                    />
                    <Text>{t('remote_storage.remember_password')}</Text>
                    <Tooltip title={t('remote_storage.remember_password_tooltip')}>
                      <Tag color="orange">{t('remote_storage.warning')}</Tag>
                    </Tooltip>
              </Space>
                </>
              )}
            </Space>
            
            <Button
              type="primary"
              loading={connecting}
              onClick={() => handleConnect()}
              style={{ marginTop: 16 }}
            >
              {t('unified_remote.connect')}
            </Button>
          </Card>
        )}
        
        {/* Directory Browser & Sync Configuration */}
        {sshConnected && (
          <Card>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {/* Sync Mode Selection */}
              <div>
                <Text strong style={{ marginRight: 16 }}>{t('remote_storage.sync.mode')}:</Text>
                <Radio.Group value={syncMode} onChange={(e) => setSyncMode(e.target.value)}>
                  <Radio.Button value="smart">
            <Space>
                      <ThunderboltOutlined />
              {t('unified_remote.mode.smart')}
              <Tag color="blue">{t('unified_remote.mode.smart_tag')}</Tag>
            </Space>
                  </Radio.Button>
                  <Radio.Button value="mirror">
                    <Space>
                      <CloudSyncOutlined />
                      {t('unified_remote.mode.mirror')}
                    </Space>
                  </Radio.Button>
                </Radio.Group>
              </div>
              
              {/* Mode Description */}
              <Alert
                type={syncMode === 'smart' ? 'info' : 'warning'}
                showIcon
                message={syncMode === 'smart' ? t('remote_storage.features.advantages') : t('unified_remote.mirror.title')}
                description={
                  syncMode === 'smart' ? (
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      <li><strong>{t('remote_storage.features.fast_init')}</strong>: {t('remote_storage.features.fast_init_desc')}</li>
                      <li><strong>{t('remote_storage.features.save_space')}</strong>: {t('remote_storage.features.save_space_desc')}</li>
                      <li><strong>{t('remote_storage.features.on_demand')}</strong>: {t('remote_storage.features.on_demand_desc')}</li>
                    </ul>
                  ) : (
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      <li>{t('unified_remote.mirror.desc_1')}</li>
                      <li>{t('unified_remote.mirror.desc_2')}</li>
                      <li>{t('unified_remote.mirror.desc_4')}</li>
                    </ul>
                  )
                }
              />
              
              {/* Directory Browser */}
              <Card title={t('remote.choose.title')} size="small">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {/* Current Path */}
                  <Space>
                    <Text>{t('remote.current_dir')}</Text>
                    <Text code>{currentPath}</Text>
                    <Button size="small" icon={<UpOutlined />} onClick={handlePathUp}>
                      {t('remote.up')}
                    </Button>
                    <Button 
                      size="small" 
                      icon={<ReloadOutlined />} 
                      loading={listing} 
                      onClick={() => listRemoteDir(currentPath)}
                    >
                      {t('remote.refresh')}
                    </Button>
                  </Space>
                  
                  {/* Directory Listing */}
                  <div style={{ 
                    maxHeight: 300, 
                    overflow: 'auto', 
                    border: '1px solid #f0f0f0', 
                    borderRadius: 4, 
                    padding: 8 
                  }}>
                    {listing ? (
                      <div style={{ textAlign: 'center', padding: 20 }}>
                        <Spin />
                      </div>
                    ) : items.length === 0 ? (
                      <Empty 
                        image={Empty.PRESENTED_IMAGE_SIMPLE} 
                        description={t('remote.empty')} 
                      />
                    ) : (
                      items.map(item => (
                        <div
                          key={item.path}
                          style={{
                            cursor: item.type === 'dir' ? 'pointer' : 'default',
                            padding: '4px 8px',
                            borderRadius: 4,
                            transition: 'background 0.2s',
                            background: selectedPath === item.path ? '#e6f7ff' : 'transparent',
                          }}
                          onMouseEnter={(e) => {
                            if (item.type === 'dir' && selectedPath !== item.path) {
                              e.currentTarget.style.background = '#f5f5f5'
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (selectedPath !== item.path) {
                              e.currentTarget.style.background = 'transparent'
                            }
                          }}
                          onClick={() => {
                            if (item.type === 'dir') {
                              setSelectedPath(item.path)
                              listRemoteDir(item.path)
                            }
                          }}
                        >
                          <Space>
                            {item.type === 'dir' ? 
                              <FolderOpenOutlined style={{ color: '#1890ff' }} /> : 
                              <FileOutlined />
                            }
                            <Text strong={item.type === 'dir'}>
                              {item.name}
                            </Text>
                            {item.type === 'file' && item.size > 0 && (
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                ({(item.size / 1024).toFixed(1)} KB)
                              </Text>
                            )}
                          </Space>
                        </div>
                      ))
                    )}
                  </div>
                  
                  {/* Selected Path */}
                  <Space style={{ width: '100%' }}>
                    <Text>{t('remote_storage.form.remote_root')}:</Text>
                    <Input 
                      value={selectedPath || currentPath}
                      onChange={(e) => setSelectedPath(e.target.value)}
                      style={{ flex: 1 }}
                      placeholder={t('remote_storage.form.remote_root_placeholder')}
                    />
                  </Space>
                  
                  {/* Sync Options */}
                  <Space style={{ width: '100%' }}>
                    {syncMode === 'smart' ? (
                      <>
                        <Switch
                          checked={autoSync}
                          onChange={setAutoSync}
                        />
                        <Text>{t('remote_storage.form.auto_sync')}</Text>
                        {autoSync && (
                          <>
                            <Text>{t('remote_storage.form.auto_sync_interval')}</Text>
                            <InputNumber
                              value={syncInterval}
                              onChange={(val) => setSyncInterval(val || 10)}
                              min={1}
                              max={60}
                              style={{ width: 80 }}
                            />
                            <Text>{t('remote_storage.form.auto_sync_interval_suffix')}</Text>
                          </>
                        )}
                      </>
                    ) : (
                      <>
                        <Text>{t('remote.interval.suffix')}:</Text>
                        <InputNumber
                          value={mirrorInterval}
                          onChange={(val) => setMirrorInterval(val || 2)}
                          min={1}
                          max={60}
                          style={{ width: 100 }}
                          addonAfter={t('remote.interval.suffix')}
                        />
                      </>
                    )}
                  </Space>
                  
                  {/* Start Sync Button */}
                  <Button 
                    type="primary" 
                    icon={syncMode === 'smart' ? <DatabaseOutlined /> : <SyncOutlined />}
                    onClick={handleStartSync}
                    disabled={!selectedPath}
                    block
                  >
                    {syncMode === 'smart' ? 
                      t('remote_storage.form.connect_button') : 
                      t('remote.sync_dir')
                    }
                  </Button>
                  
                  <Alert
                    type="info"
                    message={t('remote.tip')}
                    closable
                  />
                </Space>
              </Card>
              
              {/* Smart Mode: Sync Status */}
              {syncMode === 'smart' && smartActive && (
                <Card size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      <Badge status="success" />
                      <Text strong>{t('remote_storage.status.connected')}</Text>
                    </Space>
                    
                    <Descriptions size="small" column={2}>
                      <Descriptions.Item label={t('remote_storage.status.remote_dir')}>
                        {selectedPath}
                      </Descriptions.Item>
                    </Descriptions>
                    
                    <Space>
                      <Button icon={<SyncOutlined />} onClick={handleManualSync} loading={syncing}>
                        {t('remote_storage.status.manual_sync')}
                      </Button>
                      <Button onClick={handleVerify}>
                        {t('remote_storage.status.verify')}
                      </Button>
                    </Space>
                  </Space>
              </Card>
            )}
            
              {/* Mirror Mode: Tasks */}
              {syncMode === 'mirror' && mirrors.length > 0 && (
                <Card title={t('remote.tasks.title')} size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {mirrors.map(mirror => (
                      <Card key={mirror.id} size="small" style={{ background: '#fafafa' }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                            <Space direction="vertical" size="small">
                              <Text strong>{mirror.remote_root}</Text>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                → {mirror.local_root}
                              </Text>
                            </Space>
                            <Badge 
                              status={mirror.alive ? 'processing' : 'default'} 
                              text={mirror.alive ? t('unified_remote.mirror.status_running') : t('unified_remote.mirror.status_stopped')}
            />
          </Space>
                          
                          <Descriptions size="small" column={3}>
                            <Descriptions.Item label={t('unified_remote.mirror.copied')}>
                              {mirror.stats.copied_files || 0}
                            </Descriptions.Item>
                            <Descriptions.Item label={t('unified_remote.mirror.appended')}>
                              {mirror.stats.appended_bytes || 0} B
                            </Descriptions.Item>
                            <Descriptions.Item label={t('unified_remote.mirror.scans')}>
                              {mirror.stats.scans || 0}
                            </Descriptions.Item>
                          </Descriptions>
                          
                          {mirror.alive && (
                            <Button 
                              size="small" 
                              danger 
                              icon={<StopOutlined />}
                              onClick={() => handleStopMirror(mirror.id)}
                            >
                              {t('remote.tasks.stop')}
                            </Button>
                          )}
                        </Space>
                      </Card>
                    ))}
                  </Space>
                </Card>
              )}
            </Space>
              </Card>
            )}
          </Space>
    </div>
  )
}