/**
 * Performance Monitor Page
 * 
 * Real-time system performance monitoring with tabbed interface
 * Monitors: CPU, Memory, Disk, GPU
 */

import { useEffect, useState } from 'react'
import { Card, Space, Alert, Typography, Tag, Tooltip, Tabs, Empty } from 'antd'
import { 
  ThunderboltOutlined, 
  DashboardOutlined,
  DatabaseOutlined,
  FireOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { getSystemMonitor } from '../api'
import GpuMetricsCard from '../components/GpuMetricsCard'
import GpuTelemetry from '../components/GpuTelemetry'
import CpuDetailCard from '../components/CpuDetailCard'
import MemoryDiskCard from '../components/MemoryDiskCard'
import { useSettings } from '../contexts/SettingsContext'
import { useGpuTelemetry } from '../contexts/GpuTelemetryContext'

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

/** Shape of the /system/monitor API response. */
interface SystemMetrics {
  available: boolean
  platform?: { system: string; release: string }
  cpu?: { percent: number; [key: string]: any }
  memory?: Record<string, any>
  disk?: Record<string, any>
}

export default function PerformanceMonitorPage() {
  const { t } = useTranslation()
  const { settings } = useSettings()
  const gpu = useGpuTelemetry()

  // Derive GPU state from global context
  const gpuAvailable = gpu.available
  const gpuReason = gpu.reason
  const lastSample = gpu.samples[gpu.samples.length - 1]
  const gpus: GpuData[] = lastSample?.gpus || []
  const gpuLoading = gpu.available === null

  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null)
  const [systemLoading, setSystemLoading] = useState(true)

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
    timer = setInterval(poll, (settings.refreshInterval ?? 2) * 1000)
    
    return () => clearInterval(timer)
  }, [settings.refreshInterval])

  // Build tab items based on settings
  const tabItems = []

  // CPU Tab - check if CPU data is valid (not null and has required fields)
  if (settings.showCpuTab !== false && systemMetrics?.cpu && systemMetrics.cpu.percent !== undefined) {
    tabItems.push({
      key: 'cpu',
      label: (
        <span>
          <ThunderboltOutlined style={{ marginRight: 6 }} />
          {t('performance.tab_cpu', 'CPU')}
        </span>
      ),
      children: <CpuDetailCard cpu={systemMetrics.cpu} loading={systemLoading} />
    })
  }

  // Memory & Disk Tab
  if (settings.showMemoryDiskTab !== false && systemMetrics?.memory && systemMetrics?.disk) {
    tabItems.push({
      key: 'memory-disk',
      label: (
        <span>
          <DatabaseOutlined style={{ marginRight: 6 }} />
          {t('performance.tab_memory_disk', 'Memory & Disk')}
        </span>
      ),
      children: <MemoryDiskCard memory={systemMetrics.memory} disk={systemMetrics.disk} loading={systemLoading} />
    })
  }

  // GPU Metrics Tab
  if (settings.showGpuMetricsTab !== false && gpuAvailable && gpus.length > 0) {
    tabItems.push({
      key: 'gpu-metrics',
      label: (
        <span>
          <FireOutlined style={{ marginRight: 6 }} />
          {t('performance.tab_gpu_metrics', 'GPU Metrics')}
        </span>
      ),
      children: <GpuMetricsCard gpus={gpus} loading={gpuLoading} />
    })
  }

  // GPU Telemetry Tab
  if (settings.showGpuTelemetryTab !== false && gpuAvailable) {
    tabItems.push({
      key: 'gpu-telemetry',
      label: (
        <span>
          <ThunderboltOutlined style={{ marginRight: 6 }} />
          {t('performance.tab_gpu_telemetry', 'GPU Telemetry')}
        </span>
      ),
      children: <GpuTelemetry />
    })
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
              <Title level={4} style={{ margin: 0 }}>
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

      {/* Main content: Tabs - fills remaining space */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
      {tabItems.length > 0 ? (
        <Tabs 
          items={tabItems}
          defaultActiveKey="cpu"
          size="large"
        />
      ) : (
        <Card>
          <Empty 
            description={t('performance.no_tabs', 'No monitoring tabs enabled. Please enable tabs in Settings.')}
          />
        </Card>
      )}

      {/* GPU Not Available Warning */}
      {gpuAvailable === false && settings.showGpuMetricsTab !== false && (
        <Alert
          type="info"
          message={t('gpu.not_available')}
          description={gpuReason || t('gpu.no_nvidia_smi')}
          showIcon
          style={{ marginTop: 16 }}
        />
      )}
      </div>
    </div>
  )
}
