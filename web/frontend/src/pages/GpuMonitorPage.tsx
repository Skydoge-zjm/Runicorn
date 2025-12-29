/**
 * GPU Monitor Page
 * 
 * Real-time GPU monitoring with metrics and telemetry charts.
 * Independent page with continuous polling when open.
 */

import React, { useEffect, useState, useRef } from 'react'
import { Card, Space, Alert, Typography, Tag, Tooltip } from 'antd'
import { ThunderboltOutlined, DashboardOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { getGpuTelemetry, getSystemMonitor } from '../api'
import GpuMetricsCard from '../components/GpuMetricsCard'
import GpuTelemetry from '../components/GpuTelemetry'
import SystemMetricsCard from '../components/SystemMetricsCard'

const { Title, Text } = Typography

interface GpuData {
  index?: number
  name?: string
  util_gpu?: number
  mem_used_mib?: number
  mem_total_mib?: number
  mem_used_pct?: number
  power_w?: number
  power_limit_w?: number
  temp_c?: number
}

export default function GpuMonitorPage() {
  const { t } = useTranslation()
  const [available, setAvailable] = useState<boolean | null>(null)
  const [reason, setReason] = useState<string>('')
  const [gpus, setGpus] = useState<GpuData[]>([])
  const [loading, setLoading] = useState(true)
  const [systemMetrics, setSystemMetrics] = useState<any>(null)
  const [systemLoading, setSystemLoading] = useState(true)

  // Poll GPU data for metrics card
  useEffect(() => {
    let timer: any
    const poll = async () => {
      try {
        const res = await getGpuTelemetry()
        if (!res?.available) {
          setAvailable(false)
          setReason(res?.reason || t('gpu.not_available'))
          setLoading(false)
          return
        }
        setAvailable(true)
        setGpus(res.gpus || [])
        setLoading(false)
      } catch (e: any) {
        setAvailable(false)
        setReason(e?.message || t('gpu.not_available'))
        setLoading(false)
      }
    }
    
    // Initial fetch
    poll()
    
    // Poll every 2 seconds
    timer = setInterval(poll, 2000)
    
    return () => clearInterval(timer)
  }, [t])

  // Poll system metrics
  useEffect(() => {
    let timer: any
    const poll = async () => {
      try {
        const res = await getSystemMonitor()
        if (res?.available) {
          setSystemMetrics(res)
        }
        setSystemLoading(false)
      } catch (e: any) {
        setSystemLoading(false)
      }
    }
    
    poll()
    timer = setInterval(poll, 2000)
    
    return () => clearInterval(timer)
  }, [])

  if (available === false) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        height: '100%',
        overflow: 'hidden',
        padding: 16,
      }}>
        <Card style={{ flexShrink: 0, marginBottom: 16 }}>
          <Space direction="vertical" size="small">
            <Title level={3}>
              <DashboardOutlined /> {t('gpu.monitor_title')}
            </Title>
            <Text type="secondary">
              {t('gpu.monitor_desc')}
            </Text>
          </Space>
        </Card>
        
        <Alert
          type="warning"
          message={t('gpu.not_available')}
          description={reason || t('gpu.no_nvidia_smi')}
          showIcon
        />
      </div>
    )
  }

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      overflow: 'hidden',
      padding: 16,
    }}>
      {/* Page Header - fixed height */}
      <Card style={{ flexShrink: 0, marginBottom: 16 }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Title level={3} style={{ margin: 0 }}>
                <DashboardOutlined /> {t('gpu.monitor_title')}
              </Title>
              <Tooltip title={t('gpu.polling_every_2s')}>
                <Tag color="processing">Real-time</Tag>
              </Tooltip>
            </Space>
            {gpus.length > 0 && (
              <Text type="secondary">
                {t('gpu.detail', { count: gpus.length })}
              </Text>
            )}
          </div>
          <Text type="secondary">
            {t('gpu.monitor_desc')}
          </Text>
        </Space>
      </Card>

      {/* Main content - fills remaining space with internal scroll */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* System Metrics Card */}
          {systemMetrics && systemMetrics.available && (
            <SystemMetricsCard metrics={systemMetrics} loading={systemLoading} />
          )}

          {/* GPU Metrics Card */}
          {gpus.length > 0 && (
            <GpuMetricsCard gpus={gpus} loading={loading} />
          )}

          {/* GPU Telemetry Charts */}
          <Card 
            title={
              <Space>
                <ThunderboltOutlined />
                <span>{t('gpu.telemetry_charts')}</span>
                <Tag color="cyan">{t('gpu.history_2min')}</Tag>
              </Space>
            }
          >
            <GpuTelemetry />
          </Card>
        </Space>
      </div>
    </div>
  )
}
