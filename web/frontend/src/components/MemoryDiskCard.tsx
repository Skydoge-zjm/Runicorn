/**
 * Memory and Disk Card Component
 * 
 * Displays memory and disk metrics in a combined view
 */

import React from 'react'
import { Card, Row, Col, Progress, Space, Typography, Statistic, theme, Divider } from 'antd'
import { DatabaseOutlined, HddOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

const { Text, Title } = Typography

interface MemoryMetrics {
  total: number
  available: number
  used: number
  percent: number
  swap_total: number
  swap_used: number
  swap_percent: number
}

interface DiskMetrics {
  path: string
  total: number
  used: number
  free: number
  percent: number
}

interface MemoryDiskCardProps {
  memory: MemoryMetrics
  disk: DiskMetrics
  loading?: boolean
}

const MemoryDiskCard: React.FC<MemoryDiskCardProps> = ({ memory, disk, loading = false }) => {
  const { t } = useTranslation()
  const { token } = theme.useToken()

  const getProgressColor = (percent: number) => {
    if (percent < 60) return token.colorSuccess
    if (percent < 80) return token.colorWarning
    return token.colorError
  }

  const formatBytes = (bytes: number, decimals: number = 1) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const dm = decimals < 0 ? 0 : decimals
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
  }

  return (
    <Card loading={loading}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Memory Section */}
        <div>
          <Row gutter={16} align="middle">
            <Col span={12}>
              <Statistic
                title={
                  <Space>
                    <DatabaseOutlined style={{ color: getProgressColor(memory.percent) }} />
                    <span>{t('system.memory', 'Memory')}</span>
                  </Space>
                }
                value={formatBytes(memory.used)}
                suffix={`/ ${formatBytes(memory.total)}`}
                valueStyle={{ color: getProgressColor(memory.percent), fontSize: 20 }}
              />
            </Col>
            <Col span={12}>
              <Space direction="vertical" size={4}>
                <Text type="secondary">
                  {t('system.available', 'Available')}: {formatBytes(memory.available)}
                </Text>
                <Text type="secondary">
                  {t('system.used_percent', 'Used')}: {Math.round(memory.percent)}%
                </Text>
              </Space>
            </Col>
          </Row>
          
          <Progress 
            percent={Math.round(memory.percent)}
            strokeColor={getProgressColor(memory.percent)}
            style={{ marginTop: 16 }}
          />

          {/* Swap Memory */}
          {memory.swap_total > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <Text strong>{t('system.swap', 'Swap')}</Text>
                <Text>{formatBytes(memory.swap_used)} / {formatBytes(memory.swap_total)}</Text>
              </div>
              <Progress 
                percent={Math.round(memory.swap_percent)}
                strokeColor={getProgressColor(memory.swap_percent)}
                size="small"
              />
            </div>
          )}
        </div>

        <Divider style={{ margin: 0 }} />

        {/* Disk Section */}
        <div>
          <Row gutter={16} align="middle">
            <Col span={12}>
              <Statistic
                title={
                  <Space>
                    <HddOutlined style={{ color: getProgressColor(disk.percent) }} />
                    <span>{t('system.disk', 'Disk')} ({disk.path})</span>
                  </Space>
                }
                value={formatBytes(disk.used)}
                suffix={`/ ${formatBytes(disk.total)}`}
                valueStyle={{ color: getProgressColor(disk.percent), fontSize: 20 }}
              />
            </Col>
            <Col span={12}>
              <Space direction="vertical" size={4}>
                <Text type="secondary">
                  {t('system.free', 'Free')}: {formatBytes(disk.free)}
                </Text>
                <Text type="secondary">
                  {t('system.used_percent', 'Used')}: {Math.round(disk.percent)}%
                </Text>
              </Space>
            </Col>
          </Row>
          
          <Progress 
            percent={Math.round(disk.percent)}
            strokeColor={getProgressColor(disk.percent)}
            style={{ marginTop: 16 }}
          />
        </div>
      </Space>
    </Card>
  )
}

export default MemoryDiskCard
