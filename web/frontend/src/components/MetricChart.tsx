/**
 * Unified MetricChart Component
 * 
 * Handles both single-run and multi-run (comparison) scenarios:
 * - Single run (runs.length === 1): Shows best point markers and stage separators
 * - Multi-run (runs.length > 1): Shows multiple series for comparison overlay
 */
import React, { useEffect, useMemo, useRef, useState, memo } from 'react'
import { Space, Switch, Tooltip, Slider, Select, Button, Card, Typography, Divider, theme } from 'antd'
import { ExportOutlined } from '@ant-design/icons'
import AutoResizeEChart from './AutoResizeEChart'
import { useSettings } from '../contexts/SettingsContext'
import { useTranslation } from 'react-i18next'
import designTokens from '../styles/designTokens'

const { Text } = Typography

/** Metrics data structure from API */
export interface MetricsData {
  columns: string[]
  rows: any[]
  total?: number
  sampled?: number
}

/** Single run with its metrics data */
export interface RunMetric {
  id: string
  label?: string
  metrics: MetricsData
}

/** Unified MetricChart props */
export interface MetricChartProps {
  runs: RunMetric[]
  xKey: string
  yKey: string
  title: string
  height?: number | string
  persistKey?: string
  group?: string
  showLegend?: boolean  // Default true, set false for inline compare mode
  colors?: string[]     // Custom colors for each run
  legendSelected?: Record<string, boolean>  // Control series visibility via legend
}

/** EMA smoothing function */
function ema(vals: Array<number | null>, factor: number): Array<number | null> {
  if (factor <= 0) return vals
  const alpha = 1 - factor
  let s: number | null = null
  return vals.map(v => {
    if (v == null) return null
    s = s == null ? v : alpha * v + (1 - alpha) * s
    return s
  })
}

/** Determine best value type based on metric name */
function getBestType(key: string): 'max' | 'min' | undefined {
  const k = key.toLowerCase()
  if (k.includes('loss') || k.includes('error')) return 'min'
  if (k.includes('acc') || k.includes('f1') || k.includes('auc') || k.includes('map') || k.includes('precision') || k.includes('recall')) return 'max'
  return undefined
}

const MetricChart = memo(function MetricChart({ 
  runs, xKey, yKey, title, height, persistKey, group, showLegend = true, colors = [], legendSelected 
}: MetricChartProps) {
  const { t } = useTranslation()
  const { settings } = useSettings()
  const { token } = theme.useToken()
  
  // Mode detection
  const isSingleRun = runs.length === 1
  const primaryRun = runs[0]
  const presentCols = primaryRun?.metrics?.columns || []
  
  // Chart controls
  const effectiveHeight = height ?? settings.defaultChartHeight
  const [useLog, setUseLog] = useState(false)
  const [dynamicScale, setDynamicScale] = useState(true)
  const [smoothing, setSmoothing] = useState(0)
  
  // X-axis selection (for single run mode)
  const xCandidatesPref = ['iter', 'step', 'batch', 'global_step', 'time']
  const xCandidates = useMemo(() => xCandidatesPref.filter(k => presentCols.includes(k)), [presentCols])
  const [xAxisKey, setXAxisKey] = useState<string>(xKey)
  const loadedPersistRef = useRef(false)

  // Sync xAxisKey with prop
  useEffect(() => {
    if (xKey && presentCols.includes(xKey)) {
      setXAxisKey(xKey)
    } else if (!presentCols.includes(xAxisKey)) {
      const cand = xCandidates.find(Boolean)
      if (cand) setXAxisKey(cand)
    }
  }, [xKey, presentCols, xCandidates, xAxisKey])

  // Load persisted controls
  useEffect(() => {
    if (!persistKey || loadedPersistRef.current) return
    try {
      const raw = localStorage.getItem(`MetricChart:${persistKey}`)
      if (raw) {
        const obj = JSON.parse(raw)
        if (typeof obj.useLog === 'boolean') setUseLog(obj.useLog)
        if (typeof obj.dynamicScale === 'boolean') setDynamicScale(obj.dynamicScale)
        if (typeof obj.smoothing === 'number') setSmoothing(obj.smoothing)
        if (obj.xAxisKey && presentCols.includes(obj.xAxisKey)) setXAxisKey(obj.xAxisKey)
      }
    } catch {}
    loadedPersistRef.current = true
  }, [persistKey, presentCols])

  // Persist controls
  useEffect(() => {
    if (!persistKey) return
    try {
      localStorage.setItem(`MetricChart:${persistKey}`, JSON.stringify({ useLog, dynamicScale, smoothing, xAxisKey }))
    } catch {}
  }, [persistKey, useLog, dynamicScale, smoothing, xAxisKey])

  // Build ECharts option
  const option = useMemo(() => {
    const xKeyUsed = isSingleRun && presentCols.includes(xAxisKey) ? xAxisKey : xKey
    
    // Build series for each run
    const series = runs.map((run, runIndex) => {
      const rows = run.metrics?.rows || []
      
      // Extract and normalize x values
      const xVals = rows.map((r: any) => {
        const v = r[xKeyUsed]
        const n = v === '' || v == null ? null : Number(v)
        return n == null || Number.isNaN(n) ? null : n
      })
      let xNorm = xVals
      if (xKeyUsed === 'time') {
        const base = xVals.find((v: number | null) => v != null) ?? 0
        xNorm = xVals.map((v: number | null) => (v == null ? null : v - base))
      }
      
      // Extract y values
      const yVals = rows.map((r: any) => {
        const v = r[yKey] === '' || r[yKey] == null ? null : Number(r[yKey])
        const n = v == null || Number.isNaN(v) ? null : v
        if (useLog && (n == null || n <= 0)) return null
        return n
      })
      const smoothedY = ema(yVals, Math.min(0.99, Math.max(0, smoothing)))
      
      // Build data: category axis for single run, value axis for multi-run
      let data: any
      if (isSingleRun) {
        data = smoothedY
      } else {
        const points: Array<[number, number]> = []
        for (let i = 0; i < smoothedY.length; i++) {
          const xv = xNorm[i], yv = smoothedY[i]
          if (xv != null && yv != null) points.push([xv, yv])
        }
        data = points
      }
      
      const nnz = smoothedY.filter(v => v != null).length
      const isSparse = nnz <= 12 || nnz <= Math.ceil(rows.length * 0.2)
      
      // Get color for this run from colors array
      const seriesColor = colors?.[runIndex]
      
      // For single run: use yKey as name
      // For multi-run with legendSelected: use run.id for uniqueness (legendSelected uses runId as key)
      // For multi-run without legendSelected: use label for display
      const seriesName = isSingleRun 
        ? yKey 
        : (legendSelected ? run.id : (run.label || run.id))
      
      const s: any = {
        name: seriesName,
        type: 'line',
        smooth: 0.2,
        showSymbol: isSparse,
        symbolSize: isSparse ? 6 : 4,
        connectNulls: true,
        sampling: 'lttb',
        large: true,
        data,
        // Explicitly set color for this series to ensure consistency
        ...(seriesColor && {
          lineStyle: { color: seriesColor },
          itemStyle: { color: seriesColor },
        }),
      }
      
      // Single run extras: best point marker and stage separators
      if (isSingleRun && runIndex === 0) {
        const bp = getBestType(yKey)
        if (bp) {
          s.markPoint = { data: [{ type: bp, name: bp === 'max' ? 'Best (max)' : 'Best (min)' }], symbolSize: 60 }
        }
        
        // Stage separators
        if (presentCols.includes('stage') && (xKeyUsed === 'global_step' || xKeyUsed === 'time')) {
          const stageLines: any[] = []
          let prevStage: any = rows.length ? (rows[0]?.stage ?? null) : null
          for (let i = 1; i < rows.length; i++) {
            const raw = rows[i]?.stage
            const st = (raw === undefined || raw === null || raw === '') ? prevStage : raw
            if (st !== prevStage) {
              const pos = xNorm[i]
              if (pos != null) stageLines.push({ xAxis: pos })
              prevStage = st
            }
          }
          if (stageLines.length) {
            s.markLine = { 
              silent: true, symbol: 'none', 
              lineStyle: { type: 'dashed', color: token.colorBorder, width: 1 }, 
              label: { show: false }, data: stageLines 
            }
          }
        }
      }
      return s
    })
    
    // X-axis data for single run (category axis)
    let xAxisData: any[] | undefined
    if (isSingleRun) {
      const rows = primaryRun?.metrics?.rows || []
      const xKeyUsed2 = presentCols.includes(xAxisKey) ? xAxisKey : xKey
      const xRaw = rows.map((r: any) => {
        const v = r[xKeyUsed2]
        const n = v === '' || v == null ? null : Number(v)
        return n == null || Number.isNaN(n) ? null : n
      })
      xAxisData = xKeyUsed2 === 'time' 
        ? xRaw.map((v: any) => (v == null ? null : v - (xRaw.find((x: any) => x != null) ?? 0)))
        : xRaw
    }
    
    // Legend data should match series names
    const legendData = isSingleRun 
      ? [yKey] 
      : (legendSelected ? runs.map(r => r.id) : runs.map(r => r.label || r.id))
    
    // Calculate grid top based on legend visibility
    const gridTop = !showLegend ? 45 : (runs.length > 3 ? 70 : (runs.length > 1 ? 60 : 50))
    
    // Build legend config with optional selected state for controlling visibility
    const legendConfig = showLegend 
      ? { 
          data: legendData, 
          top: designTokens.spacing.xl, 
          type: runs.length > 3 ? 'scroll' : 'plain', 
          padding: [5, 10],
          ...(legendSelected && { selected: legendSelected }),
        }
      : { 
          show: false,
          // Even when hidden, legend.selected controls series visibility
          ...(legendSelected && { selected: legendSelected }),
        }
    
    return {
      title: { text: title, left: 'center', top: designTokens.spacing.xs,
        textStyle: { fontSize: designTokens.typography.fontSize.md, fontWeight: designTokens.typography.fontWeight.semibold }
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross', label: { show: true } } },
      legend: legendConfig,
      ...(colors.length > 0 && { color: colors }),
      xAxis: isSingleRun ? { type: 'category', data: xAxisData } : { type: 'value', name: xKey },
      yAxis: { type: useLog ? 'log' : 'value', scale: dynamicScale, min: dynamicScale ? 'dataMin' : 0 },
      grid: { left: 50, right: 30, top: gridTop, bottom: 80, show: settings.showGridLines },
      dataZoom: [{ type: 'inside', throttle: 50 }, { type: 'slider', height: 18, bottom: 40 }],
      toolbox: { feature: { restore: {}, saveAsImage: {} }, right: 10 },
      series,
      animation: settings.enableChartAnimations,
      animationDuration: settings.enableChartAnimations ? 1000 : 0,
    }
  }, [runs, xKey, xAxisKey, yKey, title, useLog, dynamicScale, smoothing, presentCols, isSingleRun, primaryRun, settings, token.colorBorder, showLegend, colors, legendSelected])

  const exportCsv = () => {
    try {
      const xKeyUsed = isSingleRun && presentCols.includes(xAxisKey) ? xAxisKey : xKey
      const lines: string[] = []
      
      if (isSingleRun) {
        // Single run: simple format [x, y]
        lines.push([xKeyUsed, yKey].join(','))
        for (const r of (primaryRun?.metrics?.rows || [])) {
          const xv = r[xKeyUsed], yv = r[yKey]
          lines.push([xv == null ? '' : String(xv), yv == null ? '' : String(yv)].join(','))
        }
      } else {
        // Multi-run: include run_id column
        lines.push(['run_id', xKeyUsed, yKey].join(','))
        for (const run of runs) {
          for (const r of (run.metrics?.rows || [])) {
            const xv = r[xKeyUsed], yv = r[yKey]
            lines.push([run.id, xv == null ? '' : String(xv), yv == null ? '' : String(yv)].join(','))
          }
        }
      }
      
      const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${title.replace(/\s+/g, '_').toLowerCase()}_${Date.now()}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {}
  }

  return (
    <div>
      <Card 
        size="small"
        style={{ marginBottom: designTokens.spacing.md, borderRadius: designTokens.borderRadius.md }}
        styles={{ body: { padding: `${designTokens.spacing.sm}px ${designTokens.spacing.md}px` } }}
      >
        <Space wrap size="small" style={{ width: '100%' }}>
          <Tooltip title={t('chart.log_y_tooltip')}>
            <Switch checkedChildren={t('chart.log')} unCheckedChildren={t('chart.linear')} checked={useLog} onChange={setUseLog} size="small" />
          </Tooltip>
          <Tooltip title={t('chart.auto_scale_tooltip')}>
            <Switch checkedChildren={t('chart.auto')} unCheckedChildren={t('chart.fixed')} checked={dynamicScale} onChange={setDynamicScale} size="small" />
          </Tooltip>
          <Divider type="vertical" style={{ margin: '0 4px' }} />
          <Space size="small" style={{ minWidth: 140, maxWidth: 200 }}>
            <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs, whiteSpace: 'nowrap' }}>{t('chart.smooth')}:</Text>
            <Slider min={0} max={0.95} step={0.05} value={smoothing} onChange={(v) => setSmoothing(Array.isArray(v) ? v[0] : v)} style={{ width: 90 }} tooltip={{ formatter: (v) => v ? `${(v * 100).toFixed(0)}%` : t('chart.off') }} />
          </Space>
          {isSingleRun && (
            <>
              <Divider type="vertical" style={{ margin: '0 4px' }} />
              <Select size="small" value={presentCols.includes(xAxisKey) ? xAxisKey : xKey} style={{ minWidth: 100 }} onChange={setXAxisKey} options={(xCandidates.length ? xCandidates : [xKey]).map(k => ({ value: k, label: `${t('chart.x_axis')}: ${k}` }))} />
            </>
          )}
          <Divider type="vertical" style={{ margin: '0 4px' }} />
          <Button size="small" icon={<ExportOutlined />} onClick={exportCsv}>{t('chart.export_csv')}</Button>
        </Space>
      </Card>
      <div style={{ height: effectiveHeight as any, width: '100%' }}>
        <AutoResizeEChart option={option as any} group={group} />
      </div>
    </div>
  )

}, (prevProps, nextProps) => {
  // Custom comparison using data fingerprints for each run
  if (prevProps.runs.length !== nextProps.runs.length) return false
  
  for (let i = 0; i < prevProps.runs.length; i++) {
    const prevRun = prevProps.runs[i]
    const nextRun = nextProps.runs[i]
    
    if (prevRun.id !== nextRun.id) return false
    if (prevRun.label !== nextRun.label) return false
    
    const prevRows = prevRun.metrics?.rows
    const nextRows = nextRun.metrics?.rows
    const prevRowCount = prevRows?.length ?? 0
    const nextRowCount = nextRows?.length ?? 0
    
    if (prevRowCount !== nextRowCount) return false
    
    if (prevRowCount > 0) {
      const prevLastStep = prevRows[prevRowCount - 1]?.global_step
      const nextLastStep = nextRows[nextRowCount - 1]?.global_step
      if (prevLastStep !== nextLastStep) return false
    }
  }
  
  // Check legendSelected changes (for visibility toggle)
  const prevSelected = prevProps.legendSelected
  const nextSelected = nextProps.legendSelected
  if (prevSelected !== nextSelected) {
    if (!prevSelected || !nextSelected) return false
    const prevKeys = Object.keys(prevSelected)
    const nextKeys = Object.keys(nextSelected)
    if (prevKeys.length !== nextKeys.length) return false
    for (const key of prevKeys) {
      if (prevSelected[key] !== nextSelected[key]) return false
    }
  }
  
  // Check colors array
  const prevColors = prevProps.colors
  const nextColors = nextProps.colors
  if (prevColors !== nextColors) {
    if (!prevColors || !nextColors) return false
    if (prevColors.length !== nextColors.length) return false
    for (let i = 0; i < prevColors.length; i++) {
      if (prevColors[i] !== nextColors[i]) return false
    }
  }
  
  return (
    prevProps.xKey === nextProps.xKey &&
    prevProps.yKey === nextProps.yKey &&
    prevProps.title === nextProps.title &&
    prevProps.height === nextProps.height &&
    prevProps.persistKey === nextProps.persistKey &&
    prevProps.group === nextProps.group &&
    prevProps.showLegend === nextProps.showLegend
  )
})

export default MetricChart