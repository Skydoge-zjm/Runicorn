import React, { useState, useEffect } from 'react'
import {
  Card, Table, Select, Space, Button, Tag, Tooltip, Switch,
  Row, Col, Statistic, Progress, Alert, Divider, Badge
} from 'antd'
import {
  LineChartOutlined, BarChartOutlined, RiseOutlined, FallOutlined,
  ThunderboltOutlined, CompressOutlined, ExpandOutlined, CopyOutlined,
  TrophyOutlined, FireOutlined, BugOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useTranslation } from 'react-i18next'

interface RunMetrics {
  id: string
  project: string
  name: string
  metrics: Record<string, number[]>
  steps: number[]
  status: string
  best_metrics?: Record<string, number>
}

interface ComparisonProps {
  runs?: string[]
}

export default function MetricsComparison({ runs = [] }: ComparisonProps) {
  const { t } = useTranslation()
  const [selectedRuns, setSelectedRuns] = useState<string[]>(runs)
  const [runData, setRunData] = useState<RunMetrics[]>([])
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([])
  const [chartType, setChartType] = useState<'line' | 'bar'>('line')
  const [compareMode, setCompareMode] = useState<'overlay' | 'side-by-side'>('overlay')
  const [highlightBest, setHighlightBest] = useState(true)
  const [showStatistics, setShowStatistics] = useState(true)
  const [loading, setLoading] = useState(false)

  // Fetch run data
  useEffect(() => {
    if (selectedRuns.length === 0) return
    
    setLoading(true)
    Promise.all(
      selectedRuns.map(async (runId) => {
        const res = await fetch(`/api/runs/${runId}/metrics`)
        return res.json()
      })
    ).then(data => {
      setRunData(data)
      // Extract all available metrics
      const allMetrics = new Set<string>()
      data.forEach((run: RunMetrics) => {
        Object.keys(run.metrics || {}).forEach(m => allMetrics.add(m))
      })
      setSelectedMetrics(Array.from(allMetrics).slice(0, 4)) // Select first 4 metrics
    }).catch(err => {
      console.error('Failed to fetch run metrics:', err)
    }).finally(() => {
      setLoading(false)
    })
  }, [selectedRuns])

  // Calculate statistics
  const calculateStats = (metric: string): any[] => {
    const stats = runData.map(run => {
      const values = run.metrics[metric] || []
      if (values.length === 0) return null
      
      const validValues = values.filter(v => !isNaN(v) && isFinite(v))
      if (validValues.length === 0) return null
      
      const min = Math.min(...validValues)
      const max = Math.max(...validValues)
      const avg = validValues.reduce((a, b) => a + b, 0) / validValues.length
      const last = validValues[validValues.length - 1]
      const improvement = validValues.length > 1 
        ? ((last - validValues[0]) / Math.abs(validValues[0])) * 100 
        : 0
      
      return {
        runId: run.id,
        runName: run.name,
        min,
        max,
        avg,
        last,
        improvement
      }
    }).filter(Boolean)
    
    // Find best values
    if (stats.length > 0) {
      const bestMin = Math.min(...stats.map(s => s!.min))
      const bestMax = Math.max(...stats.map(s => s!.max))
      const bestAvg = Math.min(...stats.map(s => s!.avg))
      const bestLast = Math.min(...stats.map(s => s!.last))
      
      return stats.map(s => ({
        ...s,
        isBestMin: s!.min === bestMin,
        isBestMax: s!.max === bestMax,
        isBestAvg: s!.avg === bestAvg,
        isBestLast: s!.last === bestLast
      }))
    }
    
    return stats
  }

  // Generate chart options
  const getChartOptions = (metric: string) => {
    const series = runData.map(run => ({
      name: run.name,
      type: chartType,
      data: run.metrics[metric]?.map((v, i) => [run.steps[i] || i, v]) || [],
      smooth: chartType === 'line',
      emphasis: { focus: 'series' },
      ...(highlightBest && run.best_metrics?.[metric] === Math.min(...runData.map(r => r.best_metrics?.[metric] || Infinity)) 
        ? { lineStyle: { width: 3 }, itemStyle: { borderWidth: 2 } }
        : {})
    }))

    return {
      title: {
        text: metric,
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          animation: false,
          label: { backgroundColor: '#6a7985' }
        }
      },
      legend: {
        data: runData.map(r => r.name),
        bottom: 0
      },
      toolbox: {
        feature: {
          dataZoom: { yAxisIndex: 'none' },
          restore: {},
          saveAsImage: {}
        }
      },
      xAxis: {
        type: 'value',
        name: 'Step',
        boundaryGap: false
      },
      yAxis: {
        type: 'value',
        name: metric
      },
      series
    }
  }

  // Render comparison charts
  const renderCharts = () => {
    if (compareMode === 'overlay') {
      return (
        <Row gutter={[16, 16]}>
          {selectedMetrics.map(metric => (
            <Col key={metric} span={12}>
              <Card>
                <ReactECharts 
                  option={getChartOptions(metric)} 
                  style={{ height: 300 }}
                />
                {showStatistics && (
                  <Table
                    size="small"
                    pagination={false}
                    dataSource={calculateStats(metric) as any}
                    columns={[
                      { title: t('Run'), dataIndex: 'runName', key: 'runName', width: 150 },
                      { 
                        title: t('Min'), 
                        dataIndex: 'min', 
                        key: 'min',
                        render: (v, r: any) => (
                          <span style={{ color: r.isBestMin ? '#52c41a' : undefined }}>
                            {v?.toFixed(4)} {r.isBestMin && <TrophyOutlined />}
                          </span>
                        )
                      },
                      { 
                        title: t('Max'), 
                        dataIndex: 'max', 
                        key: 'max',
                        render: (v, r: any) => (
                          <span style={{ color: r.isBestMax ? '#52c41a' : undefined }}>
                            {v?.toFixed(4)} {r.isBestMax && <TrophyOutlined />}
                          </span>
                        )
                      },
                      { 
                        title: t('Avg'), 
                        dataIndex: 'avg', 
                        key: 'avg',
                        render: (v, r: any) => (
                          <span style={{ color: r.isBestAvg ? '#52c41a' : undefined }}>
                            {v?.toFixed(4)} {r.isBestAvg && <TrophyOutlined />}
                          </span>
                        )
                      },
                      { 
                        title: t('Last'), 
                        dataIndex: 'last', 
                        key: 'last',
                        render: (v, r: any) => (
                          <span style={{ color: r.isBestLast ? '#52c41a' : undefined }}>
                            {v?.toFixed(4)} {r.isBestLast && <TrophyOutlined />}
                          </span>
                        )
                      },
                      {
                        title: t('Trend'),
                        dataIndex: 'improvement',
                        key: 'improvement',
                        render: (v: number) => (
                          <span style={{ color: v > 0 ? '#f5222d' : '#52c41a' }}>
                            {v > 0 ? <RiseOutlined /> : <FallOutlined />} {Math.abs(v).toFixed(1)}%
                          </span>
                        )
                      }
                    ]}
                    style={{ marginTop: 16 }}
                  />
                )}
              </Card>
            </Col>
          ))}
        </Row>
      )
    } else {
      // Side-by-side mode
      return (
        <Row gutter={[16, 16]}>
          {runData.map(run => (
            <Col key={run.id} span={24 / Math.min(runData.length, 2)}>
              <Card title={<><Badge status="processing" /> {run.name}</>}>
                {selectedMetrics.map(metric => (
                  <div key={metric} style={{ marginBottom: 24 }}>
                    <ReactECharts
                      option={{
                        title: { text: metric },
                        xAxis: { type: 'category', data: run.steps },
                        yAxis: { type: 'value' },
                        series: [{
                          data: run.metrics[metric] || [],
                          type: chartType,
                          smooth: chartType === 'line'
                        }]
                      }}
                      style={{ height: 200 }}
                    />
                  </div>
                ))}
              </Card>
            </Col>
          ))}
        </Row>
      )
    }
  }

  // Winner summary
  const renderWinnerSummary = () => {
    const winners: Record<string, Record<string, number>> = {}
    
    selectedMetrics.forEach(metric => {
      const stats = calculateStats(metric)
      stats.forEach((s: any) => {
        if (!winners[s.runName]) winners[s.runName] = { wins: 0 }
        if (s.isBestMin) winners[s.runName].wins++
        if (s.isBestLast) winners[s.runName].wins++
      })
    })
    
    const sortedWinners = Object.entries(winners).sort((a, b) => b[1].wins - a[1].wins)
    
    if (sortedWinners.length === 0) return null
    
    return (
      <Alert
        message={
          <Space>
            <TrophyOutlined style={{ color: '#faad14', fontSize: 20 }} />
            <span>{t('Best Performing Run:')}</span>
            <Tag color="gold">{sortedWinners[0][0]}</Tag>
            <span>{t(`with ${sortedWinners[0][1].wins} best metrics`)}</span>
          </Space>
        }
        type="success"
        showIcon={false}
        style={{ marginBottom: 16 }}
      />
    )
  }

  return (
    <div>
      {/* Controls */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            mode="multiple"
            placeholder={t('Select metrics to compare')}
            style={{ minWidth: 300 }}
            value={selectedMetrics}
            onChange={setSelectedMetrics}
            options={Array.from(new Set(runData.flatMap(r => Object.keys(r.metrics || {})))).map(m => ({
              label: m,
              value: m
            }))}
          />
          
          <Select
            value={chartType}
            onChange={setChartType}
            style={{ width: 100 }}
            options={[
              { label: <><LineChartOutlined /> Line</>, value: 'line' },
              { label: <><BarChartOutlined /> Bar</>, value: 'bar' }
            ]}
          />
          
          <Select
            value={compareMode}
            onChange={setCompareMode}
            style={{ width: 150 }}
            options={[
              { label: <><CompressOutlined /> Overlay</>, value: 'overlay' },
              { label: <><ExpandOutlined /> Side by Side</>, value: 'side-by-side' }
            ]}
          />
          
          <Space>
            <Switch
              checked={highlightBest}
              onChange={setHighlightBest}
              checkedChildren={t('Highlight Best')}
              unCheckedChildren={t('Normal')}
            />
            
            <Switch
              checked={showStatistics}
              onChange={setShowStatistics}
              checkedChildren={t('Show Stats')}
              unCheckedChildren={t('Hide Stats')}
            />
          </Space>
        </Space>
      </Card>

      {/* Winner Summary */}
      {highlightBest && renderWinnerSummary()}

      {/* Anomaly Detection Alert */}
      {runData.some(run => 
        selectedMetrics.some(metric => 
          run.metrics[metric]?.some(v => isNaN(v) || !isFinite(v))
        )
      ) && (
        <Alert
          message={t('Anomaly Detected')}
          description={t('Some runs contain NaN or Inf values which may indicate training issues')}
          type="warning"
          icon={<BugOutlined />}
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Charts */}
      {loading ? (
        <Card loading />
      ) : (
        renderCharts()
      )}
    </div>
  )
}
