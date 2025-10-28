/**
 * CPU Detail Card Component
 * 
 * Displays detailed CPU metrics including per-core utilization
 */

import React from 'react'
import { Card, Row, Col, Progress, Space, Typography, Statistic, theme } from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

const { Text, Title } = Typography

interface CpuMetrics {
  percent: number
  count: number
  logical_count: number
  per_core?: number[]
  frequency?: {
    current: number
    min: number
    max: number
  }
  load_avg?: number[]
}

interface CpuDetailCardProps {
  cpu: CpuMetrics
  loading?: boolean
}

const CpuDetailCard: React.FC<CpuDetailCardProps> = ({ cpu, loading = false }) => {
  const { t } = useTranslation()
  const { token } = theme.useToken()

  const getProgressColor = (percent: number) => {
    if (percent < 60) return token.colorSuccess
    if (percent < 80) return token.colorWarning
    return token.colorError
  }

  return (
    <Card loading={loading}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Overall CPU Usage */}
        <div>
          <Row gutter={16} align="middle">
            <Col span={12}>
              <Statistic
                title={
                  <Space>
                    <ThunderboltOutlined style={{ color: getProgressColor(cpu.percent) }} />
                    <span>{t('system.cpu_overall', 'Overall CPU Usage')}</span>
                  </Space>
                }
                value={cpu.percent}
                precision={1}
                suffix="%"
                valueStyle={{ color: getProgressColor(cpu.percent) }}
              />
            </Col>
            <Col span={12}>
              <Space direction="vertical" size={4}>
                <Text type="secondary">
                  {t('system.cpu_cores', 'Cores')}: {cpu.count} ({cpu.logical_count} {t('system.logical', 'logical')})
                </Text>
                {cpu.frequency && (
                  <Text type="secondary">
                    {t('system.frequency', 'Freq')}: {Math.round(cpu.frequency.current)} MHz
                  </Text>
                )}
                {cpu.load_avg && (
                  <Text type="secondary">
                    Load: {cpu.load_avg.map(l => l.toFixed(2)).join(', ')}
                  </Text>
                )}
              </Space>
            </Col>
          </Row>
          
          <Progress 
            percent={Math.round(cpu.percent)}
            strokeColor={getProgressColor(cpu.percent)}
            style={{ marginTop: 16 }}
          />
        </div>

        {/* Per-Core Usage */}
        {cpu.per_core && cpu.per_core.length > 0 && (
          <div>
            <Title level={5} style={{ marginBottom: 16 }}>
              {t('system.cpu_per_core', 'Per-Core Utilization')}
            </Title>
            <Row gutter={[16, 16]}>
              {cpu.per_core.map((corePercent, index) => (
                <Col xs={24} sm={12} md={8} lg={6} key={index}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text strong>Core {index}</Text>
                      <Text>{Math.round(corePercent)}%</Text>
                    </div>
                    <Progress 
                      percent={Math.round(corePercent)}
                      strokeColor={getProgressColor(corePercent)}
                      size="small"
                      showInfo={false}
                    />
                  </div>
                </Col>
              ))}
            </Row>
          </div>
        )}

        {/* CPU Frequency Details */}
        {cpu.frequency && (
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title={t('system.freq_current', 'Current Freq')}
                value={cpu.frequency.current}
                precision={0}
                suffix="MHz"
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title={t('system.freq_min', 'Min Freq')}
                value={cpu.frequency.min}
                precision={0}
                suffix="MHz"
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title={t('system.freq_max', 'Max Freq')}
                value={cpu.frequency.max}
                precision={0}
                suffix="MHz"
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
          </Row>
        )}
      </Space>
    </Card>
  )
}

export default CpuDetailCard
