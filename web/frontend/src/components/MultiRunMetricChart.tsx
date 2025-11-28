import React, { useEffect, useMemo, useRef, useState, memo } from 'react'
import { Space, Switch, Tooltip, Slider, Button, Card, Typography, Divider } from 'antd'
import { ExportOutlined } from '@ant-design/icons'
import AutoResizeEChart from './AutoResizeEChart'
import { useSettings } from '../contexts/SettingsContext'
import { useTranslation } from 'react-i18next'
import designTokens from '../styles/designTokens'

const { Text } = Typography

export type RunMetric = { id: string; label?: string; metrics: { columns: string[]; rows: any[] } }

function ema(vals: Array<number | null>, alpha: number) {
  if (!alpha) return vals
  let s: number | null = null
  return vals.map((v) => {
    if (v == null) { s = null; return null }
    s = s == null ? v : alpha * v + (1 - alpha) * s
    return s
  })
}

const MultiRunMetricChart = memo(function MultiRunMetricChart({
  runs,
  xKey,
  yKey,
  title,
  height,
  persistKey,
  group,
}: {
  runs: RunMetric[]
  xKey: 'global_step' | 'time'
  yKey: string
  title: string
  height?: number | string
  persistKey?: string
  group?: string
}) {
  const { t } = useTranslation()
  const { settings } = useSettings()
  
  // Use settings-based height if not explicitly provided
  const effectiveHeight = height ?? settings.defaultChartHeight
  const [useLog, setUseLog] = useState(false)
  const [dynamicScale, setDynamicScale] = useState(true)
  const [smoothing, setSmoothing] = useState(0)
  const loadedRef = useRef(false)

  // load persisted controls
  useEffect(() => {
    if (!persistKey || loadedRef.current) return
    try {
      const raw = localStorage.getItem(`MultiRunMetric:${persistKey}`)
      if (raw) {
        const obj = JSON.parse(raw)
        if (typeof obj.useLog === 'boolean') setUseLog(obj.useLog)
        if (typeof obj.dynamicScale === 'boolean') setDynamicScale(obj.dynamicScale)
        if (typeof obj.smoothing === 'number') setSmoothing(obj.smoothing)
      }
    } catch {}
    loadedRef.current = true
  }, [persistKey])

  // persist controls
  useEffect(() => {
    if (!persistKey) return
    try { localStorage.setItem(`MultiRunMetric:${persistKey}`, JSON.stringify({ useLog, dynamicScale, smoothing })) } catch {}
  }, [persistKey, useLog, dynamicScale, smoothing])

  const option = useMemo(() => {
    const series = runs.map((r) => {
      const cols = r.metrics?.columns || []
      const rows = r.metrics?.rows || []
      const xVals: Array<number | null> = rows.map((row: any) => {
        const v = row[xKey]
        const n = v === '' || v == null ? null : Number(v)
        return n == null || Number.isNaN(n) ? null : n
      })
      // For time axis, normalize to start at 0 per-run for readability when overlay
      let xs = xVals
      if (xKey === 'time') {
        const base = xVals.find(v => v != null) ?? 0
        xs = xVals.map(v => (v == null ? null : v - base))
      }
      const yVals: Array<number | null> = rows.map((row: any) => {
        const v = row[yKey]
        const n = v === '' || v == null ? null : Number(v)
        if (useLog && (n == null || n <= 0)) return null
        return n == null || Number.isNaN(n) ? null : n
      })
      const smooth = ema(yVals, Math.min(0.95, Math.max(0, smoothing)))
      const points: Array<[number, number]> = []
      for (let i = 0; i < smooth.length; i++) {
        const xv = xs[i]
        const yv = smooth[i]
        if (xv != null && yv != null) points.push([xv, yv])
      }
      return {
        name: r.label || r.id,
        type: 'line',
        smooth: true,
        showSymbol: points.length <= 12,
        symbolSize: points.length <= 12 ? 6 : 4,
        connectNulls: true,
        sampling: 'lttb',
        large: true,
        data: points, // Show all data points for experiment comparison
      } as any
    })

    return {
      title: { 
        text: title,
        left: 'center',
        top: designTokens.spacing.xs,
        textStyle: {
          fontSize: designTokens.typography.fontSize.md,
          fontWeight: designTokens.typography.fontWeight.semibold
        }
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross', label: { show: true } } },
      legend: { 
        data: runs.map(r => r.label || r.id),
        top: designTokens.spacing.xl,
        type: 'scroll',
        padding: [5, 10],
      },
      xAxis: { type: 'value', name: xKey },
      yAxis: { type: useLog ? 'log' : 'value', scale: dynamicScale, min: dynamicScale ? 'dataMin' : 0 },
      grid: { 
        left: 50, 
        right: 30, 
        // Increase top spacing for legend, especially with multiple runs
        top: runs.length > 3 ? 70 : (runs.length > 1 ? 60 : 50), 
        bottom: 80,
        show: settings.showGridLines
      },
      dataZoom: [
        { type: 'inside', throttle: 50 },
        { type: 'slider', height: 18, bottom: 40 }
      ],
      toolbox: { feature: { restore: {}, saveAsImage: {} }, right: 10 },
      series,
      animation: settings.enableChartAnimations,
      animationDuration: settings.enableChartAnimations ? 1000 : 0,
    }
  }, [runs, xKey, yKey, title, useLog, dynamicScale, smoothing, settings.enableChartAnimations, settings.maxDataPoints, settings.showGridLines])

  const exportCsv = () => {
    try {
      const header = ['run_id', xKey, yKey]
      const lines: string[] = [header.join(',')]
      for (const r of runs) {
        const rows = r.metrics?.rows || []
        for (const row of rows) {
          const xv = row[xKey]; const yv = row[yKey]
          const a = [r.id, xv == null ? '' : String(xv), yv == null ? '' : String(yv)]
          lines.push(a.join(','))
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
        style={{ 
          marginBottom: designTokens.spacing.md,
          borderRadius: designTokens.borderRadius.md,
        }}
        bodyStyle={{ padding: `${designTokens.spacing.sm}px ${designTokens.spacing.md}px` }}
      >
        {/* Use simple Space wrap layout - prevents overlap in narrow columns */}
        <Space wrap size="small" style={{ width: '100%' }}>
          {/* Y-Axis Toggles */}
          <Tooltip title={t('chart.log_y_tooltip')}>
            <Switch 
              checkedChildren={t('chart.log')} 
              unCheckedChildren={t('chart.linear')} 
              checked={useLog} 
              onChange={setUseLog} 
              size="small"
            />
          </Tooltip>

          <Tooltip title={t('chart.auto_scale_tooltip')}>
            <Switch 
              checkedChildren={t('chart.auto')} 
              unCheckedChildren={t('chart.fixed')} 
              checked={dynamicScale} 
              onChange={setDynamicScale} 
              size="small"
            />
          </Tooltip>

          <Divider type="vertical" style={{ margin: '0 4px' }} />

          {/* Smoothing Control */}
          <Space size="small" style={{ minWidth: 140, maxWidth: 200 }}>
            <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs, whiteSpace: 'nowrap' }}>
              {t('chart.smooth')}:
            </Text>
            <Slider 
              min={0} 
              max={0.95} 
              step={0.05} 
              value={smoothing} 
              onChange={(v) => setSmoothing(Array.isArray(v) ? v[0] : v)} 
              style={{ width: 90 }} 
              tooltip={{ 
                formatter: (v) => v ? `${(v * 100).toFixed(0)}%` : t('chart.off')
              }}
            />
          </Space>

          <Divider type="vertical" style={{ margin: '0 4px' }} />

          {/* Export Button */}
          <Button 
            size="small" 
            icon={<ExportOutlined />} 
            onClick={exportCsv}
          >
            {t('chart.export_csv')}
          </Button>
        </Space>
      </Card>

      <div style={{ height: effectiveHeight as any, width: '100%' }}>
        <AutoResizeEChart 
          option={option as any} 
          group={group} 
        />
      </div>
    </div>
  )
}, (prevProps, nextProps) => {
  // Custom deep comparison for performance optimization
  // Avoids expensive JSON.stringify by using data fingerprints
  
  // Compare runs array length first (fast check)
  if (prevProps.runs.length !== nextProps.runs.length) return false
  
  // Compare each run by fingerprint (id + row count + last step)
  for (let i = 0; i < prevProps.runs.length; i++) {
    const prevRun = prevProps.runs[i]
    const nextRun = nextProps.runs[i]
    
    // Check run identity
    if (prevRun.id !== nextRun.id) return false
    if (prevRun.label !== nextRun.label) return false
    
    // Check data fingerprint
    const prevRows = prevRun.metrics?.rows
    const nextRows = nextRun.metrics?.rows
    const prevRowCount = prevRows?.length ?? 0
    const nextRowCount = nextRows?.length ?? 0
    
    if (prevRowCount !== nextRowCount) return false
    
    // Compare last step if rows exist
    if (prevRowCount > 0) {
      const prevLastStep = prevRows[prevRowCount - 1]?.global_step
      const nextLastStep = nextRows[nextRowCount - 1]?.global_step
      if (prevLastStep !== nextLastStep) return false
    }
  }
  
  return (
    prevProps.xKey === nextProps.xKey &&
    prevProps.yKey === nextProps.yKey &&
    prevProps.title === nextProps.title &&
    prevProps.height === nextProps.height &&
    prevProps.persistKey === nextProps.persistKey &&
    prevProps.group === nextProps.group
  )
})

export default MultiRunMetricChart
