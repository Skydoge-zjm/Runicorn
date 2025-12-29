import React, { useEffect, useState } from 'react'
import { Card, Descriptions, Space, Button, Typography, Spin, message, Tag, Alert } from 'antd'
import { CopyOutlined, ReloadOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { health, getConfig } from '../api'
import { useTranslation } from 'react-i18next'

const { Text, Title } = Typography

export default function SystemInfoPanel() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [systemInfo, setSystemInfo] = useState<any>(null)
  
  const loadSystemInfo = async () => {
    setLoading(true)
    try {
      const [healthData, configData] = await Promise.all([
        health(),
        getConfig(),
      ])
      
      setSystemInfo({
        health: healthData,
        config: configData,
      })
    } catch (error) {
      console.error('Failed to load system info:', error)
      message.error('Failed to load system information')
    } finally {
      setLoading(false)
    }
  }
  
  useEffect(() => {
    loadSystemInfo()
  }, [])
  
  const copyToClipboard = () => {
    if (!systemInfo) return
    
    const configFile = systemInfo.config.config_file || 'Not available'
    const rateLimitConfig = systemInfo.config.config_file 
      ? systemInfo.config.config_file.replace('config.json', 'rate_limits.json')
      : 'Not available'
    
    const info = `
Runicorn System Information
===========================

Version Information:
- Runicorn: ${systemInfo.health.version}
- Status: ${systemInfo.health.status}

Storage Configuration:
- Storage Root: ${systemInfo.config.storage || systemInfo.config.user_root_dir || 'Not configured'}

Configuration Files:
- Main Config: ${configFile}
- Rate Limit Config: ${rateLimitConfig}

Cache Statistics:
- Enabled: ${systemInfo.health.cache?.enabled || 'N/A'}
- Hit Rate: ${systemInfo.health.cache?.hit_rate || 'N/A'}
- Hits: ${systemInfo.health.cache?.hits || 0}
- Misses: ${systemInfo.health.cache?.misses || 0}
- Size: ${systemInfo.health.cache?.size || 0}/${systemInfo.health.cache?.max_size || 0}

Generated: ${new Date().toLocaleString()}
`.trim()
    
    navigator.clipboard.writeText(info).then(() => {
      message.success(t('settings.system_info.copied'))
    }).catch(() => {
      message.error(t('settings.system_info.copy_failed'))
    })
  }
  
  if (loading || !systemInfo) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">{t('settings.system_info.loading')}</Text>
        </div>
      </div>
    )
  }
  
  return (
    <Space direction="vertical" size="middle" style={{ width: '100%', padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>
          <InfoCircleOutlined /> {t('settings.system_info.title')}
        </Title>
        <Space>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={loadSystemInfo}
            size="small"
          >
            {t('settings.system_info.refresh')}
          </Button>
          <Button 
            icon={<CopyOutlined />} 
            onClick={copyToClipboard}
            size="small"
          >
            {t('settings.system_info.copy_all')}
          </Button>
        </Space>
      </div>
      
      {/* Version Information */}
      <Card size="small" title={t('settings.system_info.version_info')}>
        <Descriptions column={1} size="small">
          <Descriptions.Item label={t('settings.system_info.runicorn_version')}>
            <Tag color="blue">{systemInfo.health.version}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label={t('settings.system_info.api_status')}>
            <Tag color={systemInfo.health.status === 'ok' ? 'green' : 'red'}>
              {systemInfo.health.status.toUpperCase()}
            </Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>
      
      {/* Storage Configuration */}
      <Card size="small" title={t('settings.system_info.storage_config')}>
        <Descriptions column={1} size="small">
          <Descriptions.Item label={t('settings.system_info.storage_root')}>
            <Text code copyable>{systemInfo.config.storage || systemInfo.config.user_root_dir || 'Not configured'}</Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>
      
      {/* Configuration Files */}
      <Card size="small" title={t('settings.system_info.config_files')}>
        <Descriptions column={1} size="small">
          <Descriptions.Item label={t('settings.system_info.config_file')}>
            <Text code copyable style={{ fontSize: 12 }}>
              {systemInfo.config.config_file || 'Not available'}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label={t('settings.system_info.rate_limit_config')}>
            <Text code copyable style={{ fontSize: 12 }}>
              {systemInfo.config.config_file 
                ? systemInfo.config.config_file.replace('config.json', 'rate_limits.json')
                : 'Not available'}
            </Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>
      
      {/* Cache Statistics */}
      {systemInfo.health.cache && (
        <Card size="small" title={t('settings.system_info.cache_stats')}>
          <Descriptions column={2} size="small">
            <Descriptions.Item label={t('settings.system_info.cache_status')}>
              <Tag color={systemInfo.health.cache.enabled ? 'green' : 'default'}>
                {systemInfo.health.cache.enabled ? 'Enabled' : 'Disabled'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('settings.system_info.hit_rate')}>
              <Text strong>{systemInfo.health.cache.hit_rate}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={t('settings.system_info.hits')}>
              {systemInfo.health.cache.hits}
            </Descriptions.Item>
            <Descriptions.Item label={t('settings.system_info.misses')}>
              {systemInfo.health.cache.misses}
            </Descriptions.Item>
            <Descriptions.Item label={t('settings.system_info.cache_size')}>
              {systemInfo.health.cache.size} / {systemInfo.health.cache.max_size}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
      
    </Space>
  )
}

