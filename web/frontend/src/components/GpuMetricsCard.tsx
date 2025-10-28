/**
 * GPU Metrics Card Component
 * 
 * Displays GPU metrics with progress bars for metrics that have max values
 * Supports multiple GPUs with responsive column layout
 */

import React from 'react'
import { Card, Row, Col, Progress, Space, Typography, theme } from 'antd'
import { 
  ThunderboltOutlined, 
  DatabaseOutlined, 
  FireOutlined, 
  DashboardOutlined 
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

const { Text } = Typography

interface GpuData {
  index?: number
  name?: string
  util_gpu?: number
  mem_used_mib?: number      // Backend returns in MiB
  mem_total_mib?: number     // Backend returns in MiB
  mem_used_pct?: number
  power_w?: number
  power_limit_w?: number
  temp_c?: number
  temp_max_c?: number        // Not returned by backend, use default if needed
}

interface GpuMetricsCardProps {
  gpus: GpuData[]
  loading?: boolean
}

const GpuMetricsCard: React.FC<GpuMetricsCardProps> = ({ gpus, loading = false }) => {
  const { t } = useTranslation()
  const { token } = theme.useToken()

  if (!gpus || gpus.length === 0) {
    return null
  }

  // Calculate column span for each GPU (24 / number of GPUs, min 6)
  const colSpan = Math.max(6, Math.floor(24 / gpus.length))

  // Get progress bar color based on percentage
  const getProgressColor = (percent: number) => {
    if (percent < 60) return token.colorSuccess
    if (percent < 80) return token.colorWarning
    return token.colorError
  }

  // Render a single GPU column
  const renderGpuColumn = (gpu: GpuData, index: number) => {
    const util = Math.round(gpu.util_gpu ?? 0)
    const memPercent = Math.round(gpu.mem_used_pct ?? 
                      (gpu.mem_used_mib && gpu.mem_total_mib ? (gpu.mem_used_mib / gpu.mem_total_mib) * 100 : 0))
    
    // Power: use default max (350W) if power_limit_w is not available
    const powerLimit = gpu.power_limit_w ?? 350
    const powerPercent = gpu.power_w ? Math.round((gpu.power_w / powerLimit) * 100) : 0
    
    // Temperature: use default max (85°C) if temp_max_c is not available
    const tempLimit = gpu.temp_max_c ?? 85
    const tempPercent = gpu.temp_c ? Math.round((gpu.temp_c / tempLimit) * 100) : 0

    return (
      <Col key={index} xs={24} sm={24} md={colSpan} style={{ textAlign: 'center' }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {/* GPU Name */}
          <div>
            <Text strong style={{ fontSize: 14, color: token.colorTextSecondary }}>
              GPU {gpu.index ?? index}
            </Text>
            {gpu.name && (
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {gpu.name}
                </Text>
              </div>
            )}
          </div>

          {/* GPU Utilization */}
          <div style={{ width: '100%', paddingLeft: 16, paddingRight: 16 }}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space size={4}>
                  <DashboardOutlined style={{ color: getProgressColor(util), fontSize: 14 }} />
                  <Text style={{ fontSize: 12 }}>{t('gpu.util')}</Text>
                </Space>
                <Text strong style={{ fontSize: 12 }}>{util}%</Text>
              </div>
              <Progress 
                percent={util} 
                strokeColor={getProgressColor(util)}
                size="small"
                showInfo={false}
              />
            </Space>
          </div>

          {/* Memory */}
          <div style={{ width: '100%', paddingLeft: 16, paddingRight: 16 }}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space size={4}>
                  <DatabaseOutlined style={{ color: getProgressColor(memPercent), fontSize: 14 }} />
                  <Text style={{ fontSize: 12 }}>{t('gpu.mem')}</Text>
                </Space>
                <Text strong style={{ fontSize: 12 }}>
                  {gpu.mem_used_mib && gpu.mem_total_mib 
                    ? `${(gpu.mem_used_mib / 1024).toFixed(1)}GB / ${(gpu.mem_total_mib / 1024).toFixed(1)}GB`
                    : `${memPercent}%`}
                </Text>
              </div>
              <Progress 
                percent={memPercent} 
                strokeColor={getProgressColor(memPercent)}
                size="small"
                showInfo={false}
              />
            </Space>
          </div>

          {/* Power */}
          {gpu.power_w !== undefined && (
            <div style={{ width: '100%', paddingLeft: 16, paddingRight: 16 }}>
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space size={4}>
                    <ThunderboltOutlined style={{ color: getProgressColor(powerPercent), fontSize: 14 }} />
                    <Text style={{ fontSize: 12 }}>{t('gpu.power')}</Text>
                  </Space>
                  <Text strong style={{ fontSize: 12 }}>
                    {`${Math.round(gpu.power_w)}W / ${Math.round(powerLimit)}W`}
                  </Text>
                </div>
                <Progress 
                  percent={powerPercent} 
                  strokeColor={getProgressColor(powerPercent)}
                  size="small"
                  showInfo={false}
                />
              </Space>
            </div>
          )}

          {/* Temperature */}
          {gpu.temp_c !== undefined && (
            <div style={{ width: '100%', paddingLeft: 16, paddingRight: 16 }}>
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space size={4}>
                    <FireOutlined style={{ color: getProgressColor(tempPercent), fontSize: 14 }} />
                    <Text style={{ fontSize: 12 }}>{t('gpu.temp')}</Text>
                  </Space>
                  <Text strong style={{ fontSize: 12 }}>
                    {`${Math.round(gpu.temp_c)}°C / ${Math.round(tempLimit)}°C`}
                  </Text>
                </div>
                <Progress 
                  percent={tempPercent} 
                  strokeColor={getProgressColor(tempPercent)}
                  size="small"
                  showInfo={false}
                />
              </Space>
            </div>
          )}
        </Space>
      </Col>
    )
  }

  return (
    <Card 
      title={t('gpu.monitor_title')}
      loading={loading}
      style={{ marginTop: 16 }}
    >
      <Row gutter={[16, 24]} justify="center">
        {gpus.map((gpu, index) => renderGpuColumn(gpu, index))}
      </Row>
    </Card>
  )
}

export default GpuMetricsCard
