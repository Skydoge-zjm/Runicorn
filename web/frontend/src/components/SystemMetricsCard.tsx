/**
 * System Metrics Card Component
 * 
 * Displays system metrics (CPU, Memory, Disk) with progress bars
 * Cross-platform compatible
 */

import React from 'react'
import { Card, Row, Col, Progress, Space, Typography, Statistic, theme, Tooltip } from 'antd'
import { 
  ThunderboltOutlined,
  DatabaseOutlined,
  HddOutlined,
  DashboardOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

const { Text } = Typography

interface SystemMetrics {
  cpu?: {
    percent: number
    count: number
    logical_count: number
    per_core?: number[]
    frequency?: {
      current: number
      min: number
      max: number
    }
  }
  memory?: {
    total: number
    available: number
    used: number
    percent: number
    swap_total: number
    swap_used: number
    swap_percent: number
  }
  disk?: {
    path: string
    total: number
    used: number
    free: number
    percent: number
  }
  platform?: {
    system: string
    release: string
    machine: string
  }
}

interface SystemMetricsCardProps {
  metrics: SystemMetrics
  loading?: boolean
}

const SystemMetricsCard: React.FC<SystemMetricsCardProps> = ({ metrics, loading = false }) => {
  const { t } = useTranslation()
  const { token } = theme.useToken()

  // Get progress bar color based on percentage
  const getProgressColor = (percent: number) => {
    if (percent < 60) return token.colorSuccess
    if (percent < 80) return token.colorWarning
    return token.colorError
  }

  // Format bytes to human readable
  const formatBytes = (bytes: number, decimals: number = 1) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const dm = decimals < 0 ? 0 : decimals
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
  }

  return (
    <Card 
      title={
        <Space>
          <DashboardOutlined />
          <span>{t('system.title', 'System Metrics')}</span>
        </Space>
      }
      loading={loading}
    >
      <Row gutter={[24, 16]}>
        {/* CPU Metrics */}
        {metrics.cpu && (
          <Col xs={24} sm={12} md={8}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space size={4}>
                  <ThunderboltOutlined style={{ color: getProgressColor(metrics.cpu.percent), fontSize: 18 }} />
                  <Text strong>{t('system.cpu', 'CPU')}</Text>
                </Space>
                <Text strong style={{ fontSize: 16 }}>{Math.round(metrics.cpu.percent)}%</Text>
              </div>
              
              <Progress 
                percent={Math.round(metrics.cpu.percent)}
                strokeColor={getProgressColor(metrics.cpu.percent)}
                showInfo={false}
              />
              
              <Space direction="vertical" size={2} style={{ width: '100%' }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {t('system.cpu_cores', 'Cores')}: {metrics.cpu.count} ({metrics.cpu.logical_count} {t('system.logical', 'logical')})
                </Text>
                {metrics.cpu.frequency && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {t('system.frequency', 'Freq')}: {Math.round(metrics.cpu.frequency.current)} MHz
                  </Text>
                )}
              </Space>
            </Space>
          </Col>
        )}

        {/* Memory Metrics */}
        {metrics.memory && (
          <Col xs={24} sm={12} md={8}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space size={4}>
                  <DatabaseOutlined style={{ color: getProgressColor(metrics.memory.percent), fontSize: 18 }} />
                  <Text strong>{t('system.memory', 'Memory')}</Text>
                </Space>
                <Text strong style={{ fontSize: 16 }}>
                  {formatBytes(metrics.memory.used)} / {formatBytes(metrics.memory.total)}
                </Text>
              </div>
              
              <Progress 
                percent={Math.round(metrics.memory.percent)}
                strokeColor={getProgressColor(metrics.memory.percent)}
                showInfo={false}
              />
              
              <Space direction="vertical" size={2} style={{ width: '100%' }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {t('system.available', 'Available')}: {formatBytes(metrics.memory.available)}
                </Text>
                {metrics.memory.swap_total > 0 && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {t('system.swap', 'Swap')}: {formatBytes(metrics.memory.swap_used)} / {formatBytes(metrics.memory.swap_total)}
                  </Text>
                )}
              </Space>
            </Space>
          </Col>
        )}

        {/* Disk Metrics */}
        {metrics.disk && (
          <Col xs={24} sm={12} md={8}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space size={4}>
                  <HddOutlined style={{ color: getProgressColor(metrics.disk.percent), fontSize: 18 }} />
                  <Text strong>{t('system.disk', 'Disk')} ({metrics.disk.path})</Text>
                </Space>
                <Text strong style={{ fontSize: 16 }}>
                  {formatBytes(metrics.disk.used)} / {formatBytes(metrics.disk.total)}
                </Text>
              </div>
              
              <Progress 
                percent={Math.round(metrics.disk.percent)}
                strokeColor={getProgressColor(metrics.disk.percent)}
                showInfo={false}
              />
              
              <Space direction="vertical" size={2} style={{ width: '100%' }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {t('system.free', 'Free')}: {formatBytes(metrics.disk.free)}
                </Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {t('system.used_percent', 'Used')}: {Math.round(metrics.disk.percent)}%
                </Text>
              </Space>
            </Space>
          </Col>
        )}
      </Row>
      
      {/* Platform Info */}
      {metrics.platform && (
        <div style={{ marginTop: 16, paddingTop: 16, borderTop: `1px solid ${token.colorBorder}` }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {metrics.platform.system} {metrics.platform.release} ({metrics.platform.machine})
          </Text>
        </div>
      )}
    </Card>
  )
}

export default SystemMetricsCard
