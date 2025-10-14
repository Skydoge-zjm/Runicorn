import React, { useState, useEffect, useMemo } from 'react'
import { Card, Select, Spin, Empty, message, Space } from 'antd'
import { LineChartOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import AutoResizeEChart from './AutoResizeEChart'
import logger from '../utils/logger'

const { Option } = Select

interface PerformanceData {
  version: number
  created_at: number
  run_id: string
  status: string
  metrics: Record<string, number>
}

interface ArtifactPerformanceChartProps {
  artifactName: string
  artifactType?: string
}

export default function ArtifactPerformanceChart({ 
  artifactName, 
  artifactType 
}: ArtifactPerformanceChartProps) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [performanceHistory, setPerformanceHistory] = useState<PerformanceData[]>([])
  const [availableMetrics, setAvailableMetrics] = useState<string[]>([])
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([])

  useEffect(() => {
    loadPerformanceHistory()
  }, [artifactName])

  const loadPerformanceHistory = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (artifactType) params.append('type', artifactType)

      const response = await fetch(`/api/artifacts/${artifactName}/performance-history?${params}`)
      if (!response.ok) {
        throw new Error(`Failed to load performance history: ${response.statusText}`)
      }
      
      const data: PerformanceData[] = await response.json()
      setPerformanceHistory(data)

      // Extract all available metrics
      const metricsSet = new Set<string>()
      data.forEach(item => {
        Object.keys(item.metrics).forEach(metric => metricsSet.add(metric))
      })
      const metrics = Array.from(metricsSet).sort()
      setAvailableMetrics(metrics)

      // Auto-select top metrics
      const autoSelect = metrics.slice(0, 3)
      setSelectedMetrics(autoSelect)
    } catch (error) {
      logger.error('Failed to load performance history:', error)
      message.error(t('Failed to load performance history'))
    } finally {
      setLoading(false)
    }
  }

  // Prepare data for ECharts
  const chartOption = useMemo(() => {
    if (!performanceHistory.length || !selectedMetrics.length) {
      return null
    }

    const versions = performanceHistory
      .filter(item => item.status === 'finished')
      .map(item => `v${item.version}`)

    const series = selectedMetrics.map(metric => ({
      name: metric,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      data: performanceHistory
        .filter(item => item.status === 'finished')
        .map(item => item.metrics[metric] || 0),
    }))

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
      },
      legend: {
        data: selectedMetrics,
        top: 0,
      },
      grid: {
        left: '10%',
        right: '10%',
        bottom: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: versions,
      },
      yAxis: {
        type: 'value',
        name: t('artifact.performance.metrics'),
      },
      series,
    }
  }, [performanceHistory, selectedMetrics, t])

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (performanceHistory.length === 0) {
    return (
      <Card>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('artifact.performance.no_data')}
        />
      </Card>
    )
  }

  return (
    <Card 
      title={
        <Space>
          <LineChartOutlined />
          {t('artifact.performance.title')}
        </Space>
      }
      extra={
        <Select
          mode="multiple"
          style={{ width: 300 }}
          placeholder={t('artifact.performance.select_metrics')}
          value={selectedMetrics}
          onChange={setSelectedMetrics}
          maxTagCount={3}
        >
          {availableMetrics.map(metric => (
            <Option key={metric} value={metric}>
              {metric}
            </Option>
          ))}
        </Select>
      }
    >
      {chartOption ? (
        <div style={{ height: 400 }}>
          <AutoResizeEChart
            option={chartOption}
            style={{ height: '100%', width: '100%' }}
          />
        </div>
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('artifact.performance.select_metrics_hint')}
        />
      )}
    </Card>
  )
}
