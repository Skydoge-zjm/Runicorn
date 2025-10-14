import React, { useEffect, useState } from 'react'
import { Badge, Tooltip, Space, Typography, Popover, Button, Descriptions, Progress } from 'antd'
import { 
  CloudOutlined, 
  CloudServerOutlined, 
  SyncOutlined,
  DisconnectOutlined,
  DatabaseOutlined
} from '@ant-design/icons'
import { getRemoteStatus, remoteDisconnect, remoteSyncMetadata } from '../api'
import { useTranslation } from 'react-i18next'

const { Text } = Typography

export default function RemoteStorageIndicator() {
  const { t } = useTranslation()
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  
  // Poll status every 5 seconds
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await getRemoteStatus()
        setStatus(data)
      } catch (error) {
        setStatus({ mode: 'local', connected: false })
      }
    }
    
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    
    return () => clearInterval(interval)
  }, [])
  
  if (!status) {
    return null
  }
  
  // Local mode
  if (status.mode === 'local' || !status.connected) {
    return (
      <Tooltip title={t('remote_storage.indicator.local_mode')}>
        <Badge status="default" text={t('remote_storage.indicator.local')} />
      </Tooltip>
    )
  }
  
  // Remote mode
  const isSyncing = status.sync_progress?.status === 'running'
  const syncProgress = status.sync_progress
  const stats = status.stats
  
  // Popover content with detailed info
  const popoverContent = (
    <div style={{ width: 350 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div>
          <Text strong>{t('remote_storage.indicator.remote_status')}</Text>
        </div>
        
        <Descriptions size="small" column={1}>
          <Descriptions.Item label={t('remote_storage.indicator.connection_status')}>
            <Badge status="success" text={t('remote_storage.indicator.connected')} />
          </Descriptions.Item>
          {stats?.last_sync && (
            <Descriptions.Item label={t('remote_storage.indicator.last_sync')}>
              {new Date(stats.last_sync * 1000).toLocaleString()}
            </Descriptions.Item>
          )}
          {stats?.cached_artifacts !== undefined && (
            <Descriptions.Item label={t('remote_storage.indicator.cached_artifacts')}>
              {stats.cached_artifacts}
            </Descriptions.Item>
          )}
          {stats?.cache_size_bytes !== undefined && (
            <Descriptions.Item label={t('remote_storage.indicator.cache_size')}>
              {(stats.cache_size_bytes / (1024 * 1024)).toFixed(2)} MB
            </Descriptions.Item>
          )}
        </Descriptions>
        
        {isSyncing && syncProgress && (
          <>
            <div>
              <Text strong>{t('remote_storage.indicator.sync_progress')}</Text>
              <Progress
                percent={Math.round(syncProgress.progress_percent || 0)}
                size="small"
                status="active"
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {syncProgress.synced_files} / {syncProgress.total_files}
              </Text>
            </div>
          </>
        )}
        
        <Space>
          <Button 
            size="small" 
            icon={<SyncOutlined />}
            loading={loading}
            onClick={async () => {
              setLoading(true)
              try {
                await remoteSyncMetadata()
              } catch (error) {
                // Error handled by API
              } finally {
                setLoading(false)
              }
            }}
          >
            {t('remote_storage.indicator.sync_now')}
          </Button>
          <Button
            size="small"
            danger
            icon={<DisconnectOutlined />}
            onClick={async () => {
              try {
                await remoteDisconnect()
                window.location.reload()  // Reload to switch to local mode
              } catch (error) {
                // Error handled by API
              }
            }}
          >
            {t('remote_storage.indicator.disconnect')}
          </Button>
        </Space>
      </Space>
    </div>
  )
  
  return (
    <Popover content={popoverContent} title={null} trigger="click">
      <div style={{ cursor: 'pointer' }}>
        <Badge 
          status={isSyncing ? 'processing' : 'success'}
          text={
            <Space size={4}>
              <CloudServerOutlined />
              <span>{t('remote_storage.indicator.remote')}</span>
              {isSyncing && <SyncOutlined spin />}
            </Space>
          }
        />
      </div>
    </Popover>
  )
}

