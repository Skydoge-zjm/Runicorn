import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Card, Descriptions, Space, Alert, Popover, Tag, Switch, Select, Button, Spin, message, Tooltip, Badge } from 'antd'
import { ThunderboltOutlined, DashboardOutlined, DatabaseOutlined, FireOutlined, ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, ReloadOutlined, FullscreenOutlined, RocketOutlined } from '@ant-design/icons'
import { getRunDetail, getStepMetrics, getGpuTelemetry, listRunsByName } from '../api'
import LogsViewer from '../components/LogsViewer'
import MetricChart from '../components/MetricChart'
import GpuTelemetry from '../components/GpuTelemetry'
import MultiRunMetricChart from '../components/MultiRunMetricChart'
import RunArtifacts from '../components/RunArtifacts'
import { RunDetailSkeleton } from '../components/LoadingSkeleton'
import { useSettings } from '../contexts/SettingsContext'
import { useTranslation } from 'react-i18next'
import logger from '../utils/logger'

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

  // Compare runs (same experiment name) state
  const [runsUnderName, setRunsUnderName] = useState<any[]>([])
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

  // Load runs under same project/name for comparison once detail is available
  useEffect(() => {
    (async () => {
      if (!detail?.project || !detail?.name) { setRunsUnderName([]); return }
      try {
        const rows = await listRunsByName(detail.project, detail.name)
        setRunsUnderName(rows || [])
        // default selected: current id
        setSelectedRunIds((prev) => (prev && prev.length ? prev : [id]))
      } catch { setRunsUnderName([]) }
    })()
  }, [detail?.project, detail?.name, id])

  // Fetch overlay metrics for selected runs
  useEffect(() => {
    let aborted = false
    ;(async () => {
      const next: Record<string, { columns: string[]; rows: any[] }> = { ...overlayMetricsMap }
      for (const rid of selectedRunIds) {
        if (!next[rid]) {
          try {
            const m = await getStepMetrics(rid)
            if (!aborted) next[rid] = m
          } catch {}
        }
      }
      if (!aborted) setOverlayMetricsMap(next)
    })()
    return () => { aborted = true }
  }, [selectedRunIds])

  useEffect(() => {
    try { localStorage.setItem(`run:${id}:step:xAxis`, stepXAxis) } catch {}
  }, [id, stepXAxis])
  useEffect(() => {
    try { localStorage.setItem(`run:${id}:layout:twoCol`, twoCol ? '1' : '0') } catch {}
  }, [id, twoCol])

  // (Epoch-based progress and ETA removed)

  const trendIcon = (key: 'util' | 'mem' | 'power' | 'temp') => {
    const hist = gpuHistRef.current
    if (hist.length < 2) return null
    const last = hist[hist.length - 1]
    const prev = hist[hist.length - 2]
    const dv = (last as any)[key] - (prev as any)[key]
    if (dv >= 2) return <ArrowUpOutlined style={{ color: '#52c41a', marginLeft: 6 }} />
    if (dv <= -2) return <ArrowDownOutlined style={{ color: '#fa541c', marginLeft: 6 }} />
    return <MinusOutlined style={{ color: '#8c8c8c', marginLeft: 6 }} />
  }

  // Poll GPU telemetry for inline summary (every 2s)
  useEffect(() => {
    let timer: any
    const poll = async () => {
      try {
        const res = await getGpuTelemetry()
        if (!res?.available || !res?.gpus || !res.gpus.length) return
        const g = res.gpus
        const n = g.length
        const sum = (arr: number[]) => arr.reduce((a, b) => a + (Number.isFinite(b) ? b : 0), 0)
        const util = Math.round(sum(g.map((x: any) => Number(x.util_gpu ?? 0))) / n)
        const mem = Math.round(sum(g.map((x: any) => Number(x.mem_used_pct ?? 0))) / n)
        const power = Math.round(sum(g.map((x: any) => Number(x.power_w ?? 0))))
        const temp = Math.max(...g.map((x: any) => Number(x.temp_c ?? 0)))
        setGpu({ util, mem, power, temp, gpus: g })
        // push to history for trend
        const now = Date.now() / 1000
        const arr = gpuHistRef.current.slice()
        arr.push({ t: now, util, mem, power, temp })
        while (arr.length > 60) arr.shift()
        gpuHistRef.current = arr
      } catch {}
    }
    poll()
    timer = setInterval(poll, 2000)
    return () => clearInterval(timer)
  }, [id])

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

  // Show skeleton on initial load
  if (detailLoading && !detail) {
    return <RunDetailSkeleton />
  }

  return (
    <Space direction="vertical" size="large" style={{ 
      width: '100%', 
      maxWidth: '100%',
      overflowX: 'hidden' 
    }}>
      <Card 
        title={
          <Space>
            <span>{t('run.title', { id })}</span>
            {detail?.status && (
              <Tag color={
                detail.status === 'running' ? 'processing' :
                detail.status === 'finished' ? 'success' :
                detail.status === 'failed' ? 'error' : 'default'
              }>
                {detail.status}
              </Tag>
            )}
            {lastUpdateTime && (
              <Tooltip title={`Last updated: ${lastUpdateTime.toLocaleTimeString()}`}>
                <Badge status="processing" text="Auto-refreshing" />
              </Tooltip>
            )}
          </Space>
        }
        extra={
          <Space>
            <Tooltip title={t('metrics.more_columns_tooltip') || 'Display charts in multiple columns for better comparison'}>
              <span>{t('metrics.more_columns')} <Switch checked={twoCol} onChange={setTwoCol} /></span>
            </Tooltip>
            <Tooltip title="Manual refresh">
              <Button 
                type="text" 
                icon={<ReloadOutlined />} 
                loading={detailLoading}
                onClick={() => {
                  loadDetail()
                  loadStepMetrics()
                  message.success('Data refreshed')
                }}
              />
            </Tooltip>
          </Space>
        }
      >
        <Spin spinning={detailLoading}>
          <Descriptions
            bordered
            size="middle"
            column={{ xs: 1, sm: 1, md: 2, lg: 2, xl: 2 }}
            labelStyle={{ 
              fontWeight: 600, 
              fontSize: '14px',
              color: '#262626',
              width: '120px'
            }}
            contentStyle={{ 
              fontSize: '14px',
              color: '#595959',
              fontFamily: 'inherit'
            }}
            items={[
              { 
                key: 'project', 
                label: t('run.descriptions.project'), 
                children: detail?.project ? (
                  <Tag color="blue" style={{ fontSize: '13px', padding: '4px 8px' }}>
                    {detail.project}
                  </Tag>
                ) : '-'
              },
              { 
                key: 'name', 
                label: t('run.descriptions.name'), 
                children: detail?.name ? (
                  <Tag color="purple" style={{ fontSize: '13px', padding: '4px 8px' }}>
                    {detail.name}
                  </Tag>
                ) : '-'
              },
              { 
                key: 'status', 
                label: t('run.descriptions.status'), 
                children: detail?.status ? (
                  <Tag color={
                    detail.status === 'running' ? 'processing' :
                    detail.status === 'finished' ? 'success' :
                    detail.status === 'failed' ? 'error' : 'default'
                  } style={{ fontSize: '13px', padding: '4px 8px', fontWeight: 500 }}>
                    {detail.status.toUpperCase()}
                  </Tag>
                ) : '-'
              },
              { 
                key: 'pid', 
                label: t('run.descriptions.pid'), 
                children: detail?.pid ? (
                  <span style={{ fontSize: '14px', fontWeight: 600, color: '#1677ff' }}>
                    {detail.pid}
                  </span>
                ) : '-'
              },
              { 
                key: 'run_dir', 
                label: t('run.descriptions.dir'), 
                children: detail?.run_dir ? (
                  <div style={{ 
                    fontSize: '13px', 
                    wordBreak: 'break-all',
                    lineHeight: '1.5',
                    maxWidth: '400px',
                    color: '#595959'
                  }}>
                    {detail.run_dir}
                  </div>
                ) : '-'
              },
              { 
                key: 'logs', 
                label: t('run.descriptions.logs'), 
                children: detail?.logs ? (
                  <div style={{ 
                    fontSize: '13px', 
                    wordBreak: 'break-all',
                    lineHeight: '1.5',
                    maxWidth: '400px',
                    color: '#595959'
                  }}>
                    {detail.logs}
                  </div>
                ) : '-'
              },
            ]}
          />
        </Spin>
        <div style={{ height: 12 }} />
        <div style={{ marginBottom: 8 }}>
          <Space size="large" wrap>
            <span><DashboardOutlined style={{ marginRight: 6 }} />{t('gpu.util')} {gpu?.util ?? '-'}% {trendIcon('util')}</span>
            <span><DatabaseOutlined style={{ marginRight: 6 }} />{t('gpu.mem')} {gpu?.mem ?? '-'}% {trendIcon('mem')}</span>
            <span><ThunderboltOutlined style={{ marginRight: 6 }} />{t('gpu.power')} {gpu?.power ?? '-'} W {trendIcon('power')}</span>
            <span><FireOutlined style={{ marginRight: 6 }} />{t('gpu.temp')} {gpu?.temp ?? '-'}°C {trendIcon('temp')}</span>
            {gpu?.gpus && (
              <Popover
                placement="bottom"
                content={(
                  <div style={{ minWidth: 220 }}>
                    {gpu.gpus.map((x: any, i: number) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>{t('gpu.tooltip.item', { index: x.index, name: x.name })}</span>
                        <span style={{ color: '#555' }}>{t('gpu.tooltip.metrics', {
                          util: Math.round(x.util_gpu ?? 0),
                          mem: Math.round(x.mem_used_pct ?? 0),
                          power: Math.round(x.power_w ?? 0),
                          temp: Math.round(x.temp_c ?? 0),
                        })}</span>
                      </div>
                    ))}
                  </div>
                )}
              >
                <Tag color="blue" style={{ cursor: 'pointer' }}>{t('gpu.detail', { count: gpu.gpus.length })}</Tag>
              </Popover>
            )}
          </Space>
        </div>
      </Card>

      <Card 
        title={
          <Space>
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
                Select All Metrics
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
          <Space wrap style={{ width: '100%' }}>
            <div style={{ minWidth: 200, maxWidth: windowWidth >= 768 ? 360 : '100%' }}>
              <div style={{ marginBottom: 4, fontSize: '14px', fontWeight: 500 }}>
                {t('compare.select.runs')}
              </div>
              <Select
                mode="multiple"
                allowClear
                value={selectedRunIds}
                onChange={setSelectedRunIds as any}
                placeholder={t('compare.select.runs.placeholder')}
                style={{ width: '100%', minWidth: 200 }}
                options={(runsUnderName || []).map((r: any) => ({ value: r.id, label: r.id }))}
              />
            </div>
            <div style={{ minWidth: 200, maxWidth: windowWidth >= 768 ? 300 : '100%' }}>
              <div style={{ marginBottom: 4, fontSize: '14px', fontWeight: 500 }}>
                <Space>
                  <span>{t('compare.select.metrics')}</span>
                  <Space.Compact>
                    <Tooltip title="Common loss metrics">
                      <Button 
                        size="small" 
                        type="text"
                        onClick={() => {
                          const lossMetrics = overlayMetricCandidates.filter(k => 
                            k.toLowerCase().includes('loss') || k.toLowerCase().includes('error')
                          )
                          setOverlayKeys(lossMetrics)
                        }}
                      >
                        Loss
                      </Button>
                    </Tooltip>
                    <Tooltip title="Common accuracy metrics">
                      <Button 
                        size="small" 
                        type="text"
                        onClick={() => {
                          const accMetrics = overlayMetricCandidates.filter(k => 
                            k.toLowerCase().includes('acc') || k.toLowerCase().includes('accuracy')
                          )
                          setOverlayKeys(accMetrics)
                        }}
                      >
                        Acc
                      </Button>
                    </Tooltip>
                  </Space.Compact>
                </Space>
              </div>
              <Select
                mode="multiple"
                allowClear
                value={overlayKeys}
                onChange={setOverlayKeys as any}
                placeholder={t('compare.select.metrics.placeholder')}
                style={{ width: '100%', minWidth: 200 }}
                options={overlayMetricCandidates.map(k => ({ value: k, label: k }))}
                maxTagCount="responsive"
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
              <div>
                <div style={{ marginBottom: 4, fontSize: '14px', fontWeight: 500 }}>
                  {t('compare.stepx')}
                </div>
                <Select 
                  size="small" 
                  value={stepXAxis} 
                  onChange={v => setStepXAxis(v as any)} 
                  style={{ width: 140 }} 
                  options={[
                    { value: 'global_step', label: 'global_step' },
                    { value: 'time', label: 'time' },
                  ]} 
                />
              </div>
              <Button size="small" onClick={async () => {
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
                  padding: '8px'
                }}>
                  <MultiRunMetricChart
                    title={k}
                    xKey={stepXAxis}
                    yKey={k}
                    runs={selectedRunIds.map((rid) => ({ id: rid, metrics: overlayMetricsMap[rid] || { columns: [], rows: [] } }))}
                    height={chartHeight}
                    group={`overlay-group-${id}`}
                    persistKey={`run:${id}:overlay:${k}`}
                  />
                </div>
              ))}
            </div>
          )}
        </Space>
      </Card>

      <Card 
        title={
          <Space>
            <span>{t('metrics.title')}</span>
            <Badge count={stepMetricKeys.length} showZero style={{ backgroundColor: '#1677ff' }} />
            {metricsLoading && <Spin size="small" />}
          </Space>
        } 
        extra={(
          <Space wrap>
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
                padding: '8px'
              }}>
                <MetricChart 
                  metrics={stepMetrics} 
                  xKey={stepXAxis} 
                  yKeys={[k]} 
                  title={k} 
                  height={chartHeight}
                  group={`step-group-${id}`} 
                  persistKey={`run:${id}:step:${k}`} 
                />
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card 
        title={
          <Space>
            <span>{t('gpu.title')}</span>
            {gpu && gpu.gpus && (
              <Badge count={gpu.gpus.length} showZero style={{ backgroundColor: '#52c41a' }} />
            )}
          </Space>
        }
        extra={
          <Tooltip title={t('polling.every2s')}>
            <Tag color="processing">Auto-polling</Tag>
          </Tooltip>
        }
      >
        <GpuTelemetry />
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
