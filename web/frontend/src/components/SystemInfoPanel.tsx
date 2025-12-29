import React, { useEffect, useState } from 'react'
import { Card, Descriptions, Space, Button, Typography, Spin, message, Tag, Alert, Row, Col, Statistic, Progress, Collapse, Tooltip } from 'antd'
import { CopyOutlined, ReloadOutlined, InfoCircleOutlined, DatabaseOutlined, FolderOutlined, FileOutlined, CloudServerOutlined } from '@ant-design/icons'
import { health, getConfig, getStorageStats, StorageStats } from '../api'
import { useTranslation } from 'react-i18next'

const { Text, Title } = Typography

export default function SystemInfoPanel() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [systemInfo, setSystemInfo] = useState<any>(null)
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null)
  
  const loadSystemInfo = async () => {
    setLoading(true)
    try {
      const [healthData, configData, storageData] = await Promise.all([
        health(),
        getConfig(),
        getStorageStats().catch(() => null),
      ])
      
      setSystemInfo({
        health: healthData,
        config: configData,
      })
      setStorageStats(storageData)
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
      
      {/* Storage Statistics */}
      {storageStats && (
        <Card 
          size="small" 
          title={
            <Space>
              <DatabaseOutlined />
              <span>{t('storage.title') || 'Storage Usage'}</span>
            </Space>
          }
        >
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {/* Total */}
            <div>
              <Title level={4} style={{ margin: 0 }}>{storageStats.total.size_human}</Title>
              <Text type="secondary">{t('storage.total') || 'Total Storage'}</Text>
            </div>
            
            {/* Overview Stats */}
            <Row gutter={16}>
              <Col span={6}>
                <Statistic 
                  title={t('storage.projects') || 'Projects'} 
                  value={storageStats.runs.projects_count}
                  valueStyle={{ fontSize: 18 }}
                />
              </Col>
              <Col span={6}>
                <Statistic 
                  title={t('storage.experiments') || 'Experiments'} 
                  value={storageStats.runs.experiments_count}
                  valueStyle={{ fontSize: 18 }}
                />
              </Col>
              <Col span={6}>
                <Statistic 
                  title={t('storage.runs') || 'Runs'} 
                  value={storageStats.runs.runs_count}
                  valueStyle={{ fontSize: 18 }}
                />
              </Col>
              <Col span={6}>
                <Statistic 
                  title={t('storage.blobs') || 'CAS Blobs'} 
                  value={storageStats.archive.blobs.file_count}
                  valueStyle={{ fontSize: 18 }}
                />
              </Col>
            </Row>
            
            {/* Storage Breakdown */}
            <div>
              <Text strong style={{ marginBottom: 8, display: 'block' }}>
                {t('storage.breakdown') || 'Storage Breakdown'}
              </Text>
              
              {/* Run Data */}
              <div style={{ marginBottom: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <Text>{t('storage.run_data') || 'Run Data'}</Text>
                  <Text type="secondary">{storageStats.runs.size_human}</Text>
                </div>
                <Progress 
                  percent={storageStats.total.size_bytes > 0 ? (storageStats.runs.size_bytes / storageStats.total.size_bytes) * 100 : 0} 
                  showInfo={false} 
                  strokeColor="#52c41a"
                  size="small"
                />
              </div>
              
              {/* Archive */}
              <div style={{ marginBottom: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <Text>{t('storage.archive') || 'Archive (CAS)'}</Text>
                  <Text type="secondary">{storageStats.archive.size_human}</Text>
                </div>
                <Progress 
                  percent={storageStats.total.size_bytes > 0 ? (storageStats.archive.size_bytes / storageStats.total.size_bytes) * 100 : 0} 
                  showInfo={false} 
                  strokeColor="#1890ff"
                  size="small"
                />
              </div>
              
              {/* Index */}
              <div style={{ marginBottom: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <Text>{t('storage.index_db') || 'Index Database'}</Text>
                  <Text type="secondary">{storageStats.index.size_human}</Text>
                </div>
                <Progress 
                  percent={storageStats.total.size_bytes > 0 ? (storageStats.index.size_bytes / storageStats.total.size_bytes) * 100 : 0} 
                  showInfo={false} 
                  strokeColor="#722ed1"
                  size="small"
                />
              </div>
            </div>
            
            {/* Archive Details */}
            <Collapse 
              ghost 
              size="small"
              items={[
                {
                  key: 'archive',
                  label: (
                    <Space>
                      <Text>{t('storage.archive_details') || 'Archive Details'}</Text>
                      <Text type="secondary">({storageStats.archive.size_human})</Text>
                    </Space>
                  ),
                  children: (
                    <Descriptions column={3} size="small">
                      <Descriptions.Item label={t('storage.blobs') || 'Blobs'}>
                        {storageStats.archive.blobs.size_human} ({storageStats.archive.blobs.file_count})
                      </Descriptions.Item>
                      <Descriptions.Item label={t('storage.manifests') || 'Manifests'}>
                        {storageStats.archive.manifests.size_human} ({storageStats.archive.manifests.file_count})
                      </Descriptions.Item>
                      <Descriptions.Item label={t('storage.outputs') || 'Outputs'}>
                        {storageStats.archive.outputs.size_human} ({storageStats.archive.outputs.file_count})
                      </Descriptions.Item>
                    </Descriptions>
                  ),
                },
              ]}
            />
          </Space>
        </Card>
      )}
      
    </Space>
  )
}

