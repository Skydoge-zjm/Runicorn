import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Space, Alert, Tag, Switch, Select, Button, Spin, message, Tooltip, Badge, Row, Col, Typography, Statistic, Divider, Collapse, Tabs, theme } from 'antd'
import { ThunderboltOutlined, DashboardOutlined, DatabaseOutlined, LineChartOutlined, MinusOutlined, ReloadOutlined, RocketOutlined, ClockCircleOutlined, CalendarOutlined, FolderOpenOutlined, CheckCircleOutlined, SyncOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { getRunDetail, getStepMetrics } from '../api'
import LogsViewer from '../components/LogsViewer'
import MetricChart from '../components/MetricChart'
import RunAssets from '../components/RunAssets'
import { RunDetailSkeleton } from '../components/LoadingSkeleton'
import LazyChartWrapper from '../components/LazyChartWrapper'
import ErrorBoundary from '../components/ErrorBoundary'
import { formatDuration, formatTimestamp } from '../utils/format'
import { useSettings } from '../contexts/SettingsContext'
import { useTranslation } from 'react-i18next'
import logger from '../utils/logger'

const { Text, Title } = Typography

/**
 * Refresh interval configuration based on run status.
 * Running experiments need frequent updates, while completed ones rarely change.
 */
const REFRESH_INTERVALS = {
  running: 3000,    // 3 seconds - active experiment needs frequent updates
  finished: 60000,  // 60 seconds - completed experiment rarely changes
  failed: 30000,    // 30 seconds - failed experiment might be restarted
  default: 10000,   // 10 seconds - fallback for unknown status
} as const

/**
 * Data version tracking interface for preventing unnecessary re-renders.
 */
interface MetricsVersion {
  rowCount: number
  lastStep: number
}

export default function RunDetailPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const { settings } = useSettings()
  const { token } = theme.useToken()
  const navigate = useNavigate()
  const [detail, setDetail] = useState<any>(null)
  const [stepMetrics, setStepMetrics] = useState<{ columns: string[]; rows: any[]; total?: number; sampled?: number }>({ columns: [], rows: [] })
  const [detailLoading, setDetailLoading] = useState(false)
  const [metricsLoading, setMetricsLoading] = useState(false)
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null)
  
  // Track metrics data version to prevent unnecessary re-renders
  const metricsVersionRef = useRef<MetricsVersion>({ rowCount: 0, lastStep: 0 })
  const [stepXAxis, setStepXAxis] = useState<'global_step' | 'time'>(() => {
    try { return (localStorage.getItem(`run:${id}:step:xAxis`) as any) || 'global_step' } catch { return 'global_step' }
  })
  const [twoCol, setTwoCol] = useState<boolean>(() => {
    try { return localStorage.getItem(`run:${id}:layout:twoCol`) === '1' } catch { return true }
  })
  const [activeTab, setActiveTab] = useState('overview')
  
  // Add responsive layout detection
  const [windowWidth, setWindowWidth] = useState(window.innerWidth)
  
  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])


  const loadDetail = async (showLoading = true) => {
    if (showLoading) setDetailLoading(true)
    try {
      const result = await getRunDetail(id)
      setDetail(result)
      setLastUpdateTime(new Date())
    } catch (error) {
      logger.error('Failed to load run detail:', error)
      message.error(t('run.load_failed'))
    } finally {
      if (showLoading) setDetailLoading(false)
    }
  }

  const loadStepMetrics = async (showLoading = true) => {
    if (showLoading) setMetricsLoading(true)
    try {
      // Pass maxDataPoints setting as downsample parameter to backend
      const downsample = settings.maxDataPoints > 0 ? settings.maxDataPoints : undefined
      const result = await getStepMetrics(id, downsample)
      
      // Extract data version from response
      const rows = result.rows || []
      const newRowCount = rows.length
      const newLastStep = rows.length > 0 ? (rows[rows.length - 1]?.global_step ?? 0) : 0
      
      // Only update state if data actually changed (prevents unnecessary re-renders)
      const prev = metricsVersionRef.current
      if (newRowCount !== prev.rowCount || newLastStep !== prev.lastStep) {
        setStepMetrics(result)
        metricsVersionRef.current = { rowCount: newRowCount, lastStep: newLastStep }
        logger.debug(`Metrics updated: ${prev.rowCount} -> ${newRowCount} rows, step ${prev.lastStep} -> ${newLastStep}`)
      }
    } catch (error) {
      logger.error('Failed to load step metrics:', error)
      if (showLoading) {
        message.error(t('run.metrics_failed'))
      }
    } finally {
      if (showLoading) setMetricsLoading(false)
    }
  }

  // Compute refresh interval based on run status
  const refreshInterval = useMemo(() => {
    if (!detail) return REFRESH_INTERVALS.default
    const status = detail.status as keyof typeof REFRESH_INTERVALS
    return REFRESH_INTERVALS[status] ?? REFRESH_INTERVALS.default
  }, [detail?.status])

  // Initial data load and refresh interval setup
  useEffect(() => {
    // Reset metrics version tracking on run change
    metricsVersionRef.current = { rowCount: 0, lastStep: 0 }
    
    loadDetail()
    loadStepMetrics()
    
    // Dynamic interval based on run status
    const intervalId = setInterval(() => {
      // Silent refresh without loading indicators
      loadDetail(false)
      loadStepMetrics(false)
    }, refreshInterval)
    
    return () => clearInterval(intervalId)
  }, [id, refreshInterval, settings.maxDataPoints])


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

  const tabItems = [
    { key: 'overview', label: t('run.tabs.overview') },
    { key: 'logs', label: t('logs.title') },
    { key: 'assets', label: t('run.assets.title') },
  ]

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      overflow: 'hidden',
      padding: 16,
    }}>
      {/* Main scrollable content */}
      <div style={{ flex: 1, minHeight: 0, overflow: activeTab === 'logs' ? 'hidden' : 'auto', display: 'flex', flexDirection: 'column' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          destroyInactiveTabPane={false}
          items={tabItems}
          style={{ marginBottom: 16 }}
        />

        <div style={{ display: activeTab === 'overview' ? 'block' : 'none' }}>
          <Space direction="vertical" size="middle" style={{
            width: '100%',
            maxWidth: '100%',
          }}>
      {/* Top Header Card */}
      <Card styles={{ body: { padding: '20px 24px' } }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <Space align="center" style={{ marginBottom: 8 }}>
              <Title level={3} style={{ margin: 0 }}>{detail?.alias || id}</Title>
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
              <Tooltip title={detail?.path}>
                <Text type="secondary"><FolderOpenOutlined /> {detail?.path || 'default'}</Text>
              </Tooltip>
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
              icon={<LineChartOutlined />}
              onClick={() => navigate(`/?compare=${id}`)}
            >
              {t('run.compare_with')}
            </Button>
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
              title={t('run.stats.duration')} 
              value={detail?.duration ? formatDuration(detail.duration * 1000) : '-'} 
              prefix={<ClockCircleOutlined />} 
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Statistic 
              title={t('run.stats.total_steps')} 
              value={stepMetrics.total ?? stepMetrics.rows?.length ?? 0} 
              prefix={<ThunderboltOutlined />} 
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
             <Statistic 
              title={t('run.stats.assets')} 
              value={(detail?.assets_count || 0)} 
              prefix={<RocketOutlined />} 
            />
          </Col>
        </Row>

        {/* Collapsible Details */}
        <Collapse ghost style={{ marginTop: 16 }} items={[{
          key: '1',
          label: t('run.more_details'),
          children: (
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
          ),
        }]} />
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
            <Tooltip title={t('metrics.more_columns_tooltip')}>
              <span>{t('metrics.more_columns')} <Switch checked={twoCol} onChange={setTwoCol} /></span>
            </Tooltip>
            <span>{t('compare.stepx')} <Select size="small" value={stepXAxis} onChange={v => setStepXAxis(v as any)} style={{ width: 140 }} options={[
              { value: 'global_step', label: 'global_step' },
              { value: 'time', label: 'time' },
            ]} /></span>
            <Tooltip title={t('metrics.refresh_tooltip')}>
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
                border: `1px solid ${token.colorBorderSecondary}`,
                borderRadius: '6px',
                padding: '8px',
                backgroundColor: token.colorBgContainer
              }}>
                <ErrorBoundary fallback={t('error.chart', { key: k })}>
                  <LazyChartWrapper height={chartHeight}>
                    <MetricChart 
                      runs={[{ id, metrics: stepMetrics }]}
                      xKey={stepXAxis} 
                      yKey={k} 
                      title={k} 
                      height={chartHeight}
                      group={`step-group-${id}`} 
                      persistKey={`run:${id}:step:${k}`} 
                    />
                  </LazyChartWrapper>
                </ErrorBoundary>
              </div>
            ))}
          </div>
        )}
      </Card>
          </Space>
        </div>

        <div style={{ display: activeTab === 'assets' ? 'block' : 'none' }}>
          <Card
            title={
              <Space>
                <RocketOutlined />
                {t('run.assets.title')}
              </Space>
            }
          >
            <ErrorBoundary fallback={t('error.assets_loading')}>
              <RunAssets runId={id} />
            </ErrorBoundary>
          </Card>
        </div>

        <div style={{ display: activeTab === 'logs' ? 'flex' : 'none', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                <span>{t('logs.title')}</span>
                <Tag color="cyan">{t('logs.realtime')}</Tag>
              </Space>
            }
            styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 } }}
            style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}
          >
            <ErrorBoundary fallback={t('error.logs_loading')}>
              <LogsViewer url={logUrl} />
            </ErrorBoundary>
          </Card>
        </div>
      </div>
    </div>
  )
}
