import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Space, Switch, Tooltip, Slider, Button } from 'antd'
import AutoResizeEChart from './AutoResizeEChart'

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

export default function MultiRunMetricChart({
  runs,
  xKey,
  yKey,
  title,
  height = 360,
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
        data: points,
      } as any
    })

    return {
      title: { text: title },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross', label: { show: true } } },
      legend: { data: runs.map(r => r.label || r.id) },
      xAxis: { type: 'value', name: xKey },
      yAxis: { type: useLog ? 'log' : 'value', scale: dynamicScale, min: dynamicScale ? 'dataMin' : 0 },
      grid: { left: 40, right: 20, top: 40, bottom: 72 },
      dataZoom: [
        { type: 'inside', throttle: 50 },
        { type: 'slider', height: 18, bottom: 36 }
      ],
      toolbox: { feature: { restore: {}, saveAsImage: {} }, right: 10 },
      series,
    }
  }, [runs, xKey, yKey, title, useLog, dynamicScale, smoothing])

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
      <Space wrap style={{ marginBottom: 8 }}>
        <Tooltip title="Use logarithmic y-axis (hides non-positive values)">
          <span>Log Y <Switch checked={useLog} onChange={setUseLog} style={{ marginLeft: 6 }} /></span>
        </Tooltip>
        <Tooltip title="Dynamic y-axis (do not force start at 0)">
          <span>Auto Scale Y <Switch checked={dynamicScale} onChange={setDynamicScale} style={{ marginLeft: 6 }} /></span>
        </Tooltip>
        <Tooltip title="Exponential moving average smoothing (0 = off)">
          <span style={{ display: 'inline-flex', alignItems: 'center' }}>Smooth <Slider min={0} max={0.95} step={0.05} value={smoothing} onChange={(v) => setSmoothing(Array.isArray(v) ? v[0] : v)} style={{ width: 160, marginLeft: 6 }} /></span>
        </Tooltip>
        <Button size="small" onClick={exportCsv}>Export CSV</Button>
      </Space>
      <div style={{ height: height as any, width: '100%' }}>
        <AutoResizeEChart option={option as any} group={group} />
      </div>
    </div>
  )
}
