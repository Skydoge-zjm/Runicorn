/**
 * Performance Monitor Page
 * 
 * Real-time system performance monitoring with tabbed interface
 * Monitors: CPU, Memory, Disk, GPU
 */

import React, { useEffect, useState } from 'react'
import { Card, Space, Alert, Typography, Tag, Tooltip, Tabs, Empty } from 'antd'
import { 
  ThunderboltOutlined, 
  DashboardOutlined,
  DatabaseOutlined,
  HddOutlined,
  FireOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { getGpuTelemetry, getSystemMonitor } from '../api'
import GpuMetricsCard from '../components/GpuMetricsCard'
import GpuTelemetry from '../components/GpuTelemetry'
import CpuDetailCard from '../components/CpuDetailCard'
import MemoryDiskCard from '../components/MemoryDiskCard'
import { useSettings } from '../contexts/SettingsContext'

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

export default function PerformanceMonitorPage() {
  const { t } = useTranslation()
  const { settings: value } = useSettings()
  
  const [gpus, setGpus] = useState<GpuData[]>([])
  const [gpuAvailable, setGpuAvailable] = useState<boolean | null>(null)
  const [gpuReason, setGpuReason] = useState<string>('')
  const [gpuLoading, setGpuLoading] = useState(true)
  
  const [systemMetrics, setSystemMetrics] = useState<any>(null)
  const [systemLoading, setSystemLoading] = useState(true)

  // Poll GPU data
  useEffect(() => {
    let timer: any
    const poll = async () => {
      try {
        const res = await getGpuTelemetry()
        if (!res?.available) {
          setGpuAvailable(false)
          setGpuReason(res?.reason || t('gpu.not_available'))
          setGpuLoading(false)
          return
        }
        setGpuAvailable(true)
        setGpus(res.gpus || [])
        setGpuLoading(false)
      } catch (e: any) {
        setGpuAvailable(false)
        setGpuReason(e?.message || t('gpu.not_available'))
        setGpuLoading(false)
      }
    }
    
    poll()
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

  // Build tab items based on settings
  const tabItems = []

  // CPU Tab - check if CPU data is valid (not null and has required fields)
  if (value.showCpuTab !== false && systemMetrics?.cpu && systemMetrics.cpu.percent !== undefined) {
    tabItems.push({
      key: 'cpu',
      label: (
        <span>
          <ThunderboltOutlined />
          {t('performance.tab_cpu', 'CPU')}
        </span>
      ),
      children: <CpuDetailCard cpu={systemMetrics.cpu} loading={systemLoading} />
    })
  }

  // Memory & Disk Tab
  if (value.showMemoryDiskTab !== false && systemMetrics?.memory && systemMetrics?.disk) {
    tabItems.push({
      key: 'memory-disk',
      label: (
        <span>
          <DatabaseOutlined />
          {t('performance.tab_memory_disk', 'Memory & Disk')}
        </span>
      ),
      children: <MemoryDiskCard memory={systemMetrics.memory} disk={systemMetrics.disk} loading={systemLoading} />
    })
  }

  // GPU Metrics Tab
  if (value.showGpuMetricsTab !== false && gpuAvailable && gpus.length > 0) {
    tabItems.push({
      key: 'gpu-metrics',
      label: (
        <span>
          <FireOutlined />
          {t('performance.tab_gpu_metrics', 'GPU Metrics')}
        </span>
      ),
      children: <GpuMetricsCard gpus={gpus} loading={gpuLoading} />
    })
  }

  // GPU Telemetry Tab
  if (value.showGpuTelemetryTab !== false && gpuAvailable) {
    tabItems.push({
      key: 'gpu-telemetry',
      label: (
        <span>
          <ThunderboltOutlined />
          {t('performance.tab_gpu_telemetry', 'GPU Telemetry')}
        </span>
      ),
      children: (
        <Card>
          <GpuTelemetry />
        </Card>
      )
    })
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {/* Page Header */}
      <Card>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Title level={3} style={{ margin: 0 }}>
                <DashboardOutlined /> {t('performance.title')}
              </Title>
              <Tooltip title={t('performance.polling_hint', 'Auto-polling every 2 seconds')}>
                <Tag color="processing">Real-time</Tag>
              </Tooltip>
            </Space>
            {systemMetrics?.platform && (
              <Text type="secondary">
                {systemMetrics.platform.system} {systemMetrics.platform.release}
              </Text>
            )}
          </div>
          <Text type="secondary">
            {t('performance.desc', 'Real-time system performance monitoring (CPU, Memory, Disk, GPU)')}
          </Text>
        </Space>
      </Card>

      {/* Tabs */}
      {tabItems.length > 0 ? (
        <Tabs 
          items={tabItems}
          defaultActiveKey="cpu"
          size="large"
          destroyInactiveTabPane
        />
      ) : (
        <Card>
          <Empty 
            description={t('performance.no_tabs', 'No monitoring tabs enabled. Please enable tabs in Settings.')}
          />
        </Card>
      )}

      {/* GPU Not Available Warning */}
      {gpuAvailable === false && value.showGpuMetricsTab !== false && (
        <Alert
          type="info"
          message={t('gpu.not_available')}
          description={gpuReason || t('gpu.no_nvidia_smi')}
          showIcon
        />
      )}
    </Space>
  )
}
