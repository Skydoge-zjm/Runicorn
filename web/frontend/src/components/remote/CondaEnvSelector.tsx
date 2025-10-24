/**
 * Conda Environment Selector Component
 * 
 * Displays available conda environments for user selection
 */

import React, { useState, useEffect } from 'react'
import {
  Card,
  List,
  Radio,
  Button,
  Space,
  Tag,
  Typography,
  Alert,
  Empty,
  Spin,
  Row,
  Col,
  Modal
} from 'antd'
import {
  CheckCircleOutlined,
  RightOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { CondaEnv } from '../../types/remote'
import { getRemoteConfig, getLocalVersion } from '../../api/remote'
import DismissibleAlert from '../DismissibleAlert'

const { Text, Title } = Typography

interface CondaEnvSelectorProps {
  envs: CondaEnv[]
  connectionId: string
  onSelect: (envName: string) => void
  onCancel: () => void
  loading?: boolean
}

interface EnvVersionInfo {
  pythonVersion?: string
  runicornVersion?: string
  loading: boolean
  error?: boolean
  versionStatus?: 'ok' | 'too_old' | 'mismatch' // Version compatibility status
}

export default function CondaEnvSelector({
  envs,
  connectionId,
  onSelect,
  onCancel,
  loading = false
}: CondaEnvSelectorProps) {
  const { t } = useTranslation()
  const [selectedEnv, setSelectedEnv] = useState<string>(() => {
    // Auto-select default environment
    const defaultEnv = envs.find(e => e.isDefault)
    return defaultEnv?.name || envs[0]?.name || 'system'
  })
  
  const [localVersion, setLocalVersion] = useState<string>('')
  
  // Store version info for each environment
  const [envVersions, setEnvVersions] = useState<Record<string, EnvVersionInfo>>(() => {
    // Initialize all envs with loading state
    const initial: Record<string, EnvVersionInfo> = {}
    envs.forEach(env => {
      initial[env.name] = { loading: true }
    })
    return initial
  })
  
  // Compare version strings (simplified semantic version comparison)
  const compareVersions = (remoteVer: string, localVer: string): 'ok' | 'too_old' | 'mismatch' => {
    // Remove _dev suffix for comparison
    const cleanRemote = remoteVer.replace(/_dev.*$/, '').replace(/\.dev.*$/, '')
    const cleanLocal = localVer.replace(/_dev.*$/, '').replace(/\.dev.*$/, '')
    
    // Parse version numbers
    const parseVersion = (ver: string) => {
      const parts = ver.split('.').map(n => parseInt(n) || 0)
      return { major: parts[0] || 0, minor: parts[1] || 0, patch: parts[2] || 0 }
    }
    
    const remote = parseVersion(cleanRemote)
    const local = parseVersion(cleanLocal)
    
    // Check if remote version is < 0.5.0 (too old, no remote support)
    if (remote.major === 0 && remote.minor < 5) {
      return 'too_old'
    }
    
    // Check if versions match
    if (remote.major !== local.major || remote.minor !== local.minor) {
      return 'mismatch'
    }
    
    return 'ok'
  }
  
  // Get local version on mount
  useEffect(() => {
    const fetchLocalVersion = async () => {
      try {
        const version = await getLocalVersion()
        setLocalVersion(version)
      } catch (error) {
        console.error('Failed to get local version:', error)
        setLocalVersion('unknown')
      }
    }
    fetchLocalVersion()
  }, [])
  
  // Detect versions for all environments on mount (with concurrency limit)
  useEffect(() => {
    if (!localVersion) return // Wait for local version to be loaded
    
    const detectEnvironments = async () => {
      const CONCURRENT_LIMIT = 3 // Detect 3 environments at a time
      
      // Process environments in batches
      for (let i = 0; i < envs.length; i += CONCURRENT_LIMIT) {
        const batch = envs.slice(i, i + CONCURRENT_LIMIT)
        
        // Detect batch concurrently
        await Promise.all(
          batch.map(async (env) => {
            try {
              const config = await getRemoteConfig(connectionId, env.name)
              const versionStatus = config.runicornVersion 
                ? compareVersions(config.runicornVersion, localVersion)
                : undefined
              
              setEnvVersions(prev => ({
                ...prev,
                [env.name]: {
                  pythonVersion: config.pythonVersion,
                  runicornVersion: config.runicornVersion,
                  versionStatus,
                  loading: false,
                  error: false
                }
              }))
            } catch (error) {
              setEnvVersions(prev => ({
                ...prev,
                [env.name]: {
                  loading: false,
                  error: true
                }
              }))
            }
          })
        )
      }
    }
    
    detectEnvironments()
  }, [envs, connectionId, localVersion])

  const handleConfirm = async () => {
    let versionInfo = envVersions[selectedEnv]
    
    // If environment is still loading or not yet detected, wait for detection
    if (!versionInfo || versionInfo.loading) {
      // Show loading modal
      const loadingModal = Modal.info({
        title: t('remote.env.detecting'),
        content: (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <Spin size="large" />
            <p style={{ marginTop: 16 }}>{t('remote.env.detectingEnvironment', { env: selectedEnv })}</p>
          </div>
        ),
        okButtonProps: { style: { display: 'none' } },
        closable: false,
        maskClosable: false
      })
      
      try {
        // Force immediate detection for this environment
        const config = await getRemoteConfig(connectionId, selectedEnv)
        const versionStatus = config.runicornVersion && localVersion
          ? compareVersions(config.runicornVersion, localVersion)
          : undefined
        
        versionInfo = {
          pythonVersion: config.pythonVersion,
          runicornVersion: config.runicornVersion,
          versionStatus,
          loading: false,
          error: false
        }
        setEnvVersions(prev => ({
          ...prev,
          [selectedEnv]: versionInfo
        }))
      } catch (error) {
        versionInfo = {
          loading: false,
          error: true
        }
        setEnvVersions(prev => ({
          ...prev,
          [selectedEnv]: versionInfo
        }))
      } finally {
        loadingModal.destroy()
      }
    }
    
    // Now check the detection result
    if (!versionInfo || versionInfo.error) {
      Modal.error({
        title: t('remote.env.detectFailed'),
        content: t('remote.env.detectFailedMessage'),
        okText: t('remote.form.cancel')
      })
      return
    }
    
    if (!versionInfo.runicornVersion) {
      // Runicorn is not installed, show warning dialog
      const activateCmd = selectedEnv === 'system' 
        ? '# System Python, no activation needed'
        : `conda activate ${selectedEnv}`
      
      Modal.warning({
        title: t('remote.env.runicornNotInstalledTitle'),
        width: 600,
        content: (
          <div>
            <p>{t('remote.env.runicornNotInstalledMessage')}</p>
            <p style={{ marginTop: 16 }}>{t('remote.env.installInstructions')}</p>
            <pre style={{ 
              background: '#f5f5f5', 
              padding: '12px', 
              borderRadius: '4px',
              fontSize: '13px',
              lineHeight: '1.5'
            }}>
              <div style={{ color: '#999' }}># {t('remote.env.activateCommand')}</div>
              <div>{activateCmd}</div>
              <div style={{ marginTop: 8, color: '#999' }}># {t('remote.env.installCommand')}</div>
              <div>pip install runicorn</div>
            </pre>
          </div>
        ),
        okText: t('remote.form.cancel')
      })
      return
    }
    
    // Check version compatibility
    if (versionInfo.versionStatus === 'too_old') {
      // Version < 0.5.0, no remote viewer support
      Modal.error({
        title: t('remote.env.versionTooOldTitle'),
        width: 600,
        content: (
          <div>
            <p>{t('remote.env.versionTooOldMessage', { version: versionInfo.runicornVersion })}</p>
            <p style={{ marginTop: 16 }}>{t('remote.env.upgradeInstructions')}</p>
            <pre style={{ 
              background: '#f5f5f5', 
              padding: '12px', 
              borderRadius: '4px',
              fontSize: '13px',
              lineHeight: '1.5'
            }}>
              <div>pip install --upgrade runicorn</div>
            </pre>
          </div>
        ),
        okText: t('remote.form.cancel')
      })
      return
    }
    
    if (versionInfo.versionStatus === 'mismatch') {
      // Version mismatch, show warning but allow continue
      Modal.warning({
        title: t('remote.env.versionMismatchTitle'),
        width: 600,
        content: (
          <div>
            <p>{t('remote.env.versionMismatchMessage')}</p>
            <div style={{ marginTop: 16, padding: '12px', background: '#fff7e6', borderRadius: '4px' }}>
              <div><strong>{t('remote.env.localVersion')}:</strong> {localVersion}</div>
              <div style={{ marginTop: 4 }}><strong>{t('remote.env.remoteVersion')}:</strong> {versionInfo.runicornVersion}</div>
            </div>
            <p style={{ marginTop: 16, color: '#faad14' }}>{t('remote.env.versionMismatchWarning')}</p>
          </div>
        ),
        okText: t('remote.env.continueAnyway'),
        cancelText: t('remote.form.cancel'),
        onOk: () => {
          onSelect(selectedEnv)
        }
      })
      return // Exit here, don't continue to the next onSelect call
    }
    
    // All good, proceed
    onSelect(selectedEnv)
  }

  if (envs.length === 0) {
    return (
      <Card title={t('remote.env.title')}>
        <Empty description={t('remote.env.noEnvs')} />
        <Button onClick={onCancel} style={{ marginTop: 16 }}>
          {t('remote.form.cancel')}
        </Button>
      </Card>
    )
  }

  return (
    <Card
      title={
        <Space>
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
          <span>{t('remote.env.title')}</span>
        </Space>
      }
    >
      <DismissibleAlert
        alertId="remote.env.selectHint"
        message={t('remote.env.selectHint')}
        description={t('remote.env.selectDescription')}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Radio.Group
        value={selectedEnv}
        onChange={e => setSelectedEnv(e.target.value)}
        style={{ width: '100%' }}
      >
        <List
          dataSource={envs}
          size="small"
          renderItem={env => {
            const versionInfo = envVersions[env.name] || { loading: true }
            const getEnvTypeTag = () => {
              if (env.type === 'conda') return <Tag color="green" style={{ fontSize: '10px', padding: '0 3px', lineHeight: '14px' }}>conda</Tag>
              if (env.type === 'system') return <Tag style={{ fontSize: '10px', padding: '0 3px', lineHeight: '14px' }}>system</Tag>
              if (env.type === 'venv') return <Tag color="orange" style={{ fontSize: '10px', padding: '0 3px', lineHeight: '14px' }}>venv</Tag>
              return null
            }
            
            return (
              <List.Item
                style={{
                  cursor: 'pointer',
                  background: selectedEnv === env.name ? '#f0f5ff' : 'transparent',
                  padding: '6px 12px',
                  borderRadius: '4px',
                  marginBottom: '2px',
                  minHeight: 'auto'
                }}
                onClick={() => setSelectedEnv(env.name)}
              >
                <Row style={{ width: '100%' }} align="middle">
                  <Col flex="none" style={{ marginRight: 12 }}>
                    <Radio value={env.name} />
                  </Col>
                  <Col flex="auto">
                    {/* Left: Env name and path */}
                    <div style={{ lineHeight: '1.2' }}>
                      <div>
                        <Space size={4}>
                          <Text strong style={{ fontSize: '14px', lineHeight: '1.2' }}>{env.name}</Text>
                          {getEnvTypeTag()}
                          {env.isDefault && (
                            <Tag color="blue" style={{ fontSize: '10px', padding: '0 3px', lineHeight: '14px' }}>
                              {t('remote.env.default')}
                            </Tag>
                          )}
                        </Space>
                      </div>
                      <div style={{ marginTop: '2px' }}>
                        <Text type="secondary" code style={{ fontSize: '11px', lineHeight: '1.2' }}>
                          {env.path}
                        </Text>
                      </div>
                    </div>
                  </Col>
                  <Col flex="none" style={{ textAlign: 'right', minWidth: 140 }}>
                    {/* Right: Python and Runicorn versions */}
                    <div style={{ lineHeight: '1.2' }}>
                      <div>
                        {versionInfo.loading ? (
                          <Spin indicator={<LoadingOutlined style={{ fontSize: 12 }} />} />
                        ) : versionInfo.error ? (
                          <Text type="danger" style={{ fontSize: '11px' }}>
                            <CloseCircleOutlined /> {t('remote.env.detectFailed')}
                          </Text>
                        ) : (
                          <Text type="secondary" style={{ fontSize: '11px' }}>
                            {versionInfo.pythonVersion || 'N/A'}
                          </Text>
                        )}
                      </div>
                      <div style={{ marginTop: '2px' }}>
                        {versionInfo.loading ? (
                          <Spin indicator={<LoadingOutlined style={{ fontSize: 12 }} />} />
                        ) : versionInfo.error ? (
                          <Text type="danger" style={{ fontSize: '11px' }}>
                            N/A
                          </Text>
                        ) : versionInfo.runicornVersion ? (
                          versionInfo.versionStatus === 'too_old' ? (
                            <Text type="danger" style={{ fontSize: '11px' }}>
                              <CloseCircleOutlined /> Runicorn {versionInfo.runicornVersion}
                            </Text>
                          ) : versionInfo.versionStatus === 'mismatch' ? (
                            <Text type="warning" style={{ fontSize: '11px' }}>
                              <WarningOutlined /> Runicorn {versionInfo.runicornVersion}
                            </Text>
                          ) : (
                            <Text type="success" style={{ fontSize: '11px' }}>
                              Runicorn {versionInfo.runicornVersion}
                            </Text>
                          )
                        ) : (
                          <Text type="warning" style={{ fontSize: '11px' }}>
                            <WarningOutlined /> {t('remote.env.runicornNotInstalled')}
                          </Text>
                        )}
                      </div>
                    </div>
                  </Col>
                </Row>
              </List.Item>
            )
          }}
        />
      </Radio.Group>

      <DismissibleAlert
        alertId="remote.env.checkRunicorn"
        type="warning"
        message={t('remote.env.checkRunicorn')}
        description={t('remote.env.checkRunicornHint')}
        icon={<WarningOutlined />}
        style={{ marginTop: 16, marginBottom: 16 }}
      />

      {/* Action Buttons */}
      <Space style={{ marginTop: 16 }}>
        <Button
          type="primary"
          icon={<RightOutlined />}
          onClick={handleConfirm}
          loading={loading}
          size="large"
        >
          {t('remote.env.continue')}
        </Button>
        <Button onClick={onCancel} disabled={loading}>
          {t('remote.form.cancel')}
        </Button>
      </Space>
    </Card>
  )
}
