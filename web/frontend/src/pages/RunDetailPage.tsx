import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Card, Descriptions, Space, Alert, Popover, Tag, Switch, Select, Button, Spin, message, Tooltip, Badge, Row, Col, Typography, Statistic, Divider, Collapse } from 'antd'
import { ThunderboltOutlined, DashboardOutlined, DatabaseOutlined, FireOutlined, ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, ReloadOutlined, FullscreenOutlined, RocketOutlined, ClockCircleOutlined, CalendarOutlined, UserOutlined, FolderOpenOutlined, CheckCircleOutlined, SyncOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'
import { getRunDetail, getStepMetrics, getGpuTelemetry, listRunsByName, listNames, listProjects } from '../api'
import LogsViewer from '../components/LogsViewer'
import MetricChart from '../components/MetricChart'
import MultiRunMetricChart from '../components/MultiRunMetricChart'
import RunArtifacts from '../components/RunArtifacts'
import { RunDetailSkeleton } from '../components/LoadingSkeleton'
import FancyMetricCard from '../components/fancy/FancyMetricCard'
import CircularProgress from '../components/fancy/CircularProgress'
import AnimatedStatusBadge from '../components/fancy/AnimatedStatusBadge'
import GpuMetricsCard from '../components/GpuMetricsCard'
import LazyChartWrapper from '../components/LazyChartWrapper'
import { formatDuration, formatTimestamp } from '../utils/format'
import { useSettings } from '../contexts/SettingsContext'
import { useTranslation } from 'react-i18next'
import logger from '../utils/logger'
import designTokens from '../styles/designTokens'

const { Text, Title } = Typography
const { Panel } = Collapse

export default function RunDetailPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const { settings } = useSettings()
  const [detail, setDetail] = useState<any>(null)
  const [stepMetrics, setStepMetrics] = useState<{ columns: string[]; rows: any[] }>({ columns: [], rows: [] })
  const [detailLoading, setDetailLoading] = useState(false)
  const [metricsLoading, setMetricsLoading] = useState(false)
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null)
  const [stepXAxis, setStepXAxis] = useState<'global_step' | 'time'>(() => {
    try { return (localStorage.getItem(`run:${id}:step:xAxis`) as any) || 'global_step' } catch { return 'global_step' }
  })
  const [twoCol, setTwoCol] = useState<boolean>(() => {
    try { return localStorage.getItem(`run:${id}:layout:twoCol`) === '1' } catch { return true }
  })
  
  // Add responsive layout detection
  const [windowWidth, setWindowWidth] = useState(window.innerWidth)
  
  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])
  const [gpu, setGpu] = useState<{ util: number; mem: number; power: number; temp: number; gpus?: any[] } | null>(null)
  const gpuHistRef = useRef<Array<{ t: number; util: number; mem: number; power: number; temp: number }>>([])

  // Compare runs state
  // availableProjects: list of all projects
  const [availableProjects, setAvailableProjects] = useState<string[]>([])
  // selectedProject: currently selected project for comparison
  const [selectedProject, setSelectedProject] = useState<string>('')
  // availableExperiments: list of experiment names under the selected project
  const [availableExperiments, setAvailableExperiments] = useState<string[]>([])
  // selectedExperiment: currently selected experiment name for comparison
  const [selectedExperiment, setSelectedExperiment] = useState<string>('')
  // runsInExperiment: runs under the selected experiment name
  const [runsInExperiment, setRunsInExperiment] = useState<any[]>([])
  
  // selectedRunIds: ids of runs to compare. Initially contains current run id.
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([])
  
  const [overlayKeys, setOverlayKeys] = useState<string[]>([])
  const [overlayMetricsMap, setOverlayMetricsMap] = useState<Record<string, { columns: string[]; rows: any[] }>>({})

  const loadDetail = async (showLoading = true) => {
    if (showLoading) setDetailLoading(true)
    try {
      const result = await getRunDetail(id)
      setDetail(result)
      setLastUpdateTime(new Date())
    } catch (error) {
      logger.error('Failed to load run detail:', error)
      message.error(t('run.load_failed') || 'Failed to load run details')
    } finally {
      if (showLoading) setDetailLoading(false)
    }
  }
  
  const loadStepMetrics = async (showLoading = true) => {
    if (showLoading) setMetricsLoading(true)
    try {
      const result = await getStepMetrics(id)
      setStepMetrics(result)
    } catch (error) {
      logger.error('Failed to load step metrics:', error)
      message.error(t('run.metrics_failed') || 'Failed to load metrics')
    } finally {
      if (showLoading) setMetricsLoading(false)
    }
  }

  useEffect(() => {
    loadDetail()
    loadStepMetrics()
    const t = setInterval(() => {
      // Silent refresh without loading indicators
      loadDetail(false);
      loadStepMetrics(false);
    }, 3000)
    return () => clearInterval(t)
  }, [id])

  // Initialize comparison state when detail is loaded
  useEffect(() => {
    if (!detail?.project || !detail?.name) return
    
    // 1. Load all projects
    listProjects().then(res => setAvailableProjects(res.projects || [])).catch(() => {})

    // 2. Set default selected project/experiment to current run's info
    if (!selectedProject) {
      setSelectedProject(detail.project)
      setSelectedExperiment(detail.name)
    }
    
    // 3. Ensure current run is in selectedRunIds
    setSelectedRunIds(prev => prev.includes(id) ? prev : [id])
    
  }, [detail?.project, detail?.name, id])

  // Load experiments when selectedProject changes
  useEffect(() => {
    if (!selectedProject) {
      setAvailableExperiments([])
      return
    }
    listNames(selectedProject).then(res => {
      setAvailableExperiments(res.names || [])
      // Reset experiment selection if switching projects (unless it matches detail)
      if (selectedProject !== detail?.project) {
        setSelectedExperiment('')
      } else {
        // If back to original project, select original experiment
        setSelectedExperiment(detail?.name || '')
      }
    }).catch(() => setAvailableExperiments([]))
  }, [selectedProject, detail?.project, detail?.name])

  // Load runs when selectedExperiment changes
  useEffect(() => {
    if (!selectedProject || !selectedExperiment) {
      setRunsInExperiment([])
      return
    }
    
    listRunsByName(selectedProject, selectedExperiment).then(rows => {
      // Sort by start_time desc
      const sorted = (rows || []).sort((a: any, b: any) => (b.start_time || 0) - (a.start_time || 0))
      setRunsInExperiment(sorted)
    }).catch(() => setRunsInExperiment([]))
    
  }, [selectedProject, selectedExperiment])

  // Fetch overlay metrics for selected runs
  useEffect(() => {
    let aborted = false
    ;(async () => {
      const next: Record<string, { columns: string[]; rows: any[] }> = { ...overlayMetricsMap }
      // Remove unselected keys to save memory? Optional. 
      // For now just add missing ones.
      for (const rid of selectedRunIds) {
        if (!next[rid]) {
          try {
            const m = await getStepMetrics(rid)
            if (!aborted) next[rid] = m
          } catch {}
        }
      }
      setOverlayMetricsMap(next)
    })()
    return () => { aborted = true }
  }, [selectedRunIds])

  useEffect(() => {
    try { localStorage.setItem(`run:${id}:step:xAxis`, stepXAxis) } catch {}
  }, [id, stepXAxis])
  useEffect(() => {
    try { localStorage.setItem(`run:${id}:layout:twoCol`, twoCol ? '1' : '0') } catch {}
  }, [id, twoCol])

  const wsProto = location.protocol === 'https:' ? 'wss' : 'ws'
  const logUrl = useMemo(() => {
    const base: string = (import.meta as any).env?.VITE_API_BASE || '/api'
    if (/^https?:/i.test(base)) {
      const asWs = base.replace(/^http/i, wsProto)
      return `${asWs.replace(/\/$/, '')}/runs/${id}/logs/ws`
    }
    return `${wsProto}://${location.host}${base.replace(/\/$/, '')}/runs/${id}/logs/ws`
  }, [id, wsProto])

  // derive dynamic metric keys
  const isNumericColumn = (m: { columns: string[]; rows: any[] }, key: string) => {
    if (!m?.rows?.length) return false
    for (const r of m.rows) {
      const v = r[key]
      if (v == null || v === '') continue
      const n = Number(v)
      if (!Number.isNaN(n)) return true
    }
    return false
  }
  const skipCols = new Set(['epoch', 'global_step', 'iter', 'step', 'batch', 'time', 'stage'])
  const stepMetricKeys = useMemo(() => (stepMetrics.columns || []).filter(k => !skipCols.has(k) && isNumericColumn(stepMetrics, k)), [stepMetrics])

  // Derive union metric keys across selected runs for overlay
  const overlayMetricCandidates = useMemo(() => {
    const keys = new Set<string>()
    for (const rid of selectedRunIds) {
      const m = overlayMetricsMap[rid]
      if (!m) continue
      const cols = m.columns || []
      for (const k of cols) {
        if (!skipCols.has(k) && isNumericColumn(m, k)) keys.add(k)
      }
    }
    return Array.from(keys).sort()
  }, [selectedRunIds, overlayMetricsMap])

  const gridStyle: React.CSSProperties = useMemo(() => {
    // Force single column on narrow screens
    const effectiveTwoCol = twoCol && windowWidth >= 900
    
    return {
      display: 'grid',
      gridTemplateColumns: effectiveTwoCol ? 'repeat(auto-fit, minmax(400px, 1fr))' : '1fr',
      gap: 16,
      width: '100%',
      maxWidth: '100%',
    }
  }, [twoCol, windowWidth])
  
  // Use settings-based chart height with responsive scaling
  const chartHeight = useMemo(() => {
    const baseHeight = settings.defaultChartHeight
    if (windowWidth >= 1200) return baseHeight + 30  // Large screens
    if (windowWidth >= 900) return baseHeight        // Medium screens  
    return Math.max(250, baseHeight - 40)            // Small screens, with minimum
  }, [windowWidth, settings.defaultChartHeight])

  // Helper to get status icon
  const getStatusIcon = (status: string) => {
    switch(status) {
      case 'running': return <SyncOutlined spin style={{ color: '#1890ff' }} />
      case 'finished': return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'failed': return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
      default: return <MinusOutlined />
    }
  }

  // Show skeleton on initial load
  if (detailLoading && !detail) {
    return <RunDetailSkeleton />
  }

  return (
    <Space direction="vertical" size="middle" style={{ 
      width: '100%', 
      maxWidth: '100%',
      overflowX: 'hidden' 
    }}>
      {/* Top Header Card */}
      <Card bodyStyle={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <Space align="center" style={{ marginBottom: 8 }}>
              <Title level={3} style={{ margin: 0 }}>{detail?.name || id}</Title>
              {detail?.status && (
                <Tag 
                  icon={getStatusIcon(detail.status)} 
                  color={detail.status === 'running' ? 'processing' : detail.status === 'finished' ? 'success' : detail.status === 'failed' ? 'error' : 'default'}
                  style={{ fontSize: '14px', padding: '4px 10px', borderRadius: 4 }}
                >
                  {detail.status.toUpperCase()}
                </Tag>
              )}
            </Space>
            <Space split={<Divider type="vertical" />}>
              <Text type="secondary"><FolderOpenOutlined /> {detail?.project || 'Default Project'}</Text>
              {detail?.start_time && <Text type="secondary"><CalendarOutlined /> {formatTimestamp(detail.start_time)}</Text>}
              {detail?.pid && <Text type="secondary">PID: {detail.pid}</Text>}
            </Space>
          </div>

          <Space>
            {lastUpdateTime && (
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {t('run.updated', { time: lastUpdateTime.toLocaleTimeString() })}
              </Text>
            )}
            <Button 
              icon={<ReloadOutlined />} 
              onClick={() => { loadDetail(); loadStepMetrics(); message.success(t('run.refreshed')); }}
              loading={detailLoading}
            >
              {t('run.refresh')}
            </Button>
          </Space>
        </div>

        <Divider style={{ margin: '16px 0' }} />

        <Row gutter={[24, 16]}>
          <Col xs={24} sm={12} md={8}>
            <Statistic 
              title={t('run.stats.duration') || "Duration"} 
              value={detail?.duration ? formatDuration(detail.duration * 1000) : '-'} 
              prefix={<ClockCircleOutlined />} 
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Statistic 
              title={t('run.stats.total_steps') || "Total Steps"} 
              value={stepMetrics.rows?.length || 0} 
              prefix={<ThunderboltOutlined />} 
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
             <Statistic 
              title={t('run.stats.artifacts') || "Artifacts"} 
              value={(detail?.artifacts_created_count || 0) + (detail?.artifacts_used_count || 0)} 
              prefix={<RocketOutlined />} 
            />
          </Col>
        </Row>

        {/* Collapsible Details */}
        <Collapse ghost style={{ marginTop: 16 }}>
          <Panel header={t('run.more_details') || "More Details (Paths, Logs)"} key="1">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div>
                <Text type="secondary" style={{ display: 'inline-block', width: 100 }}>{t('run.descriptions.run_id')}:</Text>
                <Text copyable>{id}</Text>
              </div>
              <div>
                <Text type="secondary" style={{ display: 'inline-block', width: 100 }}>{t('run.descriptions.run_dir')}:</Text>
                <Text copyable ellipsis style={{ maxWidth: 'calc(100% - 120px)' }}>{detail?.run_dir}</Text>
              </div>
              <div>
                <Text type="secondary" style={{ display: 'inline-block', width: 100 }}>{t('run.descriptions.log_file')}:</Text>
                <Text copyable ellipsis style={{ maxWidth: 'calc(100% - 120px)' }}>{detail?.logs}</Text>
              </div>
            </div>
          </Panel>
        </Collapse>
      </Card>
      
      {/* GPU Metrics Card - only show when run is running */}
      {detail?.status === 'running' && gpu?.gpus && gpu.gpus.length > 0 && (
        <GpuMetricsCard gpus={gpu.gpus} loading={detailLoading} />
      )}

      <Card 
        title={
          <Space>
            <FireOutlined />
            <span>{t('compare.title')}</span>
            {selectedRunIds.length > 1 && overlayKeys.length > 0 && (
              <Badge 
                count={`${selectedRunIds.length} runs × ${overlayKeys.length} metrics`} 
                style={{ backgroundColor: '#52c41a' }} 
              />
            )}
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="Select all available metrics">
              <Button 
                size="small" 
                type="dashed"
                onClick={() => setOverlayKeys(overlayMetricCandidates)}
                disabled={overlayMetricCandidates.length === 0}
              >
                Select All
              </Button>
            </Tooltip>
            <Tooltip title="Clear all selections">
              <Button 
                size="small" 
                type="text"
                onClick={() => {
                  setOverlayKeys([])
                  setSelectedRunIds([id])  // Keep current run
                }}
              >
                Clear
              </Button>
            </Tooltip>
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Space wrap style={{ width: '100%' }} align="start">
            
            {/* Comparison Selection Area */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1, minWidth: 300 }}>
               
               {/* Project & Experiment Selector */}
               <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                 <div style={{ flex: 1, minWidth: 160 }}>
                   <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: 4 }}>{t('run.descriptions.project') || "Project"}</div>
                   <Select
                     showSearch
                     style={{ width: '100%' }}
                     value={selectedProject}
                     onChange={setSelectedProject}
                     options={availableProjects.map(n => ({ value: n, label: n }))}
                     placeholder="Select Project"
                   />
                 </div>
                 <div style={{ flex: 1, minWidth: 160 }}>
                   <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: 4 }}>{t('run.descriptions.name') || "Experiment"}</div>
                   <Select
                     showSearch
                     style={{ width: '100%' }}
                     value={selectedExperiment}
                     onChange={setSelectedExperiment}
                     options={availableExperiments.map(n => ({ value: n, label: n }))}
                     placeholder="Select Experiment"
                     disabled={!selectedProject}
                   />
                 </div>
               </div>
                 
               {/* Runs Selector */}
               <div>
                 <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: 4 }}>{t('compare.select.runs')}</div>
                 <Select
                   mode="multiple"
                   allowClear
                   style={{ width: '100%' }}
                   value={selectedRunIds}
                   onChange={setSelectedRunIds}
                   placeholder={t('compare.select.runs.placeholder')}
                   optionLabelProp="label"
                   maxTagCount={3}
                 >
                   {(runsInExperiment || []).map((r: any) => (
                     <Select.Option key={r.id} value={r.id} label={r.id.substring(0,8)}>
                       <Space direction="vertical" size={0} style={{ width: '100%' }}>
                         <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                           <Text strong>{r.id}</Text>
                           <Tag color={r.status === 'running' ? 'blue' : r.status === 'finished' ? 'green' : 'red'} style={{ marginRight: 0 }}>{r.status}</Tag>
                         </div>
                         <Text type="secondary" style={{ fontSize: 12 }}>
                           {r.start_time ? formatTimestamp(r.start_time) : '-'}
                         </Text>
                       </Space>
                     </Select.Option>
                   ))}
                 </Select>
               </div>

               {/* Metrics Selector */}
               <div>
                  <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: 4 }}>
                    <Space>
                      <span>{t('compare.select.metrics')}</span>
                      <Space.Compact size="small">
                        <Button type="text" size="small" onClick={() => setOverlayKeys(overlayMetricCandidates.filter(k => k.match(/loss|error/i)))}>Loss</Button>
                        <Button type="text" size="small" onClick={() => setOverlayKeys(overlayMetricCandidates.filter(k => k.match(/acc|accuracy/i)))}>Acc</Button>
                      </Space.Compact>
                    </Space>
                  </div>
                  <Select
                    mode="multiple"
                    allowClear
                    style={{ width: '100%' }}
                    value={overlayKeys}
                    onChange={setOverlayKeys}
                    placeholder={t('compare.select.metrics.placeholder')}
                    options={overlayMetricCandidates.map(k => ({ value: k, label: k }))}
                    maxTagCount="responsive"
                  />
               </div>
            </div>

            {/* Controls Area */}
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, paddingBottom: 4 }}>
              <div>
                <div style={{ marginBottom: 4, fontSize: '12px', color: '#8c8c8c' }}>
                  {t('compare.stepx')}
                </div>
                <Select 
                  value={stepXAxis} 
                  onChange={v => setStepXAxis(v as any)} 
                  style={{ width: 120 }} 
                  options={[
                    { value: 'global_step', label: 'global_step' },
                    { value: 'time', label: 'time' },
                  ]} 
                />
              </div>
              <Button onClick={async () => {
                const next: Record<string, { columns: string[]; rows: any[] }> = {}
                for (const rid of selectedRunIds) {
                  try { next[rid] = await getStepMetrics(rid) } catch {}
                }
                setOverlayMetricsMap(next)
              }}>{t('compare.refresh')}</Button>
            </div>
          </Space>

          {overlayKeys.length === 0 || selectedRunIds.length === 0 ? (
            <Alert type="info" showIcon message={t('compare.tip')} />
          ) : (
            <div style={gridStyle}>
              {overlayKeys.map((k) => (
                <div key={k} style={{ 
                  minWidth: 300, 
                  maxWidth: '100%', 
                  overflow: 'hidden',
                  border: '1px solid #f0f0f0',
                  borderRadius: '6px',
                  padding: '8px',
                  backgroundColor: '#fff'
                }}>
                  <LazyChartWrapper height={chartHeight}>
                    <MultiRunMetricChart
                      title={k}
                      xKey={stepXAxis}
                      yKey={k}
                      runs={selectedRunIds.map((rid) => ({ id: rid, metrics: overlayMetricsMap[rid] || { columns: [], rows: [] } }))}
                      height={chartHeight}
                      group={`overlay-group-${id}`}
                      persistKey={`run:${id}:overlay:${k}`}
                    />
                  </LazyChartWrapper>
                </div>
              ))}
            </div>
          )}
        </Space>
      </Card>

      <Card 
        title={
          <Space>
            <DashboardOutlined />
            <span>{t('metrics.title')}</span>
            <Badge count={stepMetricKeys.length} showZero style={{ backgroundColor: '#1677ff' }} />
            {metricsLoading && <Spin size="small" />}
          </Space>
        } 
        extra={(
          <Space wrap>
            <Tooltip title={t('metrics.more_columns_tooltip') || 'Display charts in multiple columns'}>
              <span>{t('metrics.more_columns')} <Switch checked={twoCol} onChange={setTwoCol} /></span>
            </Tooltip>
            <span>{t('compare.stepx')} <Select size="small" value={stepXAxis} onChange={v => setStepXAxis(v as any)} style={{ width: 140 }} options={[
              { value: 'global_step', label: 'global_step' },
              { value: 'time', label: 'time' },
            ]} /></span>
            <Tooltip title="Refresh metrics">
              <Button 
                type="text" 
                size="small"
                icon={<ReloadOutlined />}
                loading={metricsLoading}
                onClick={() => loadStepMetrics()}
              />
            </Tooltip>
          </Space>
        )}
      >
        {stepMetricKeys.length === 0 ? (
          <Alert type="info" showIcon message={t('metrics.none')} />
        ) : (
          <div style={gridStyle}>
            {stepMetricKeys.map((k) => (
              <div key={k} style={{ 
                minWidth: 300, 
                maxWidth: '100%', 
                overflow: 'hidden',
                border: '1px solid #f0f0f0',
                borderRadius: '6px',
                padding: '8px',
                backgroundColor: '#fff'
              }}>
                <LazyChartWrapper height={chartHeight}>
                  <MetricChart 
                    metrics={stepMetrics} 
                    xKey={stepXAxis} 
                    yKeys={[k]} 
                    title={k} 
                    height={chartHeight}
                    group={`step-group-${id}`} 
                    persistKey={`run:${id}:step:${k}`} 
                  />
                </LazyChartWrapper>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* 关联的模型与数据集 - 只在有artifacts时显示 */}
      {(detail?.artifacts_created_count > 0 || detail?.artifacts_used_count > 0) && (
        <Card 
          title={
            <Space>
              <RocketOutlined /> 
              {t('run.artifacts.title')}
            </Space>
          }
        >
          <RunArtifacts runId={id} />
        </Card>
      )}

      {/* 实时日志 */}
      <Card 
        title={
          <Space>
            <DatabaseOutlined />
            <span>{t('logs.title')}</span>
            <Tag color="cyan">Real-time</Tag>
          </Space>
        }
        styles={{ body: { padding: 0 } }}
      >
        <LogsViewer url={logUrl} persistKey={`run_${id}_logs`} />
      </Card>
    </Space>
  )
}
