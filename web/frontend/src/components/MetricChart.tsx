import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Space, Switch, Tooltip, Slider, Select, Button } from 'antd'
import AutoResizeEChart from './AutoResizeEChart'

export default function MetricChart({ metrics, xKey, yKeys, title, height = 360, persistKey, group }: { metrics: { columns: string[]; rows: any[] }, xKey: string, yKeys: string[], title: string, height?: number | string, persistKey?: string, group?: string }) {
  const [useLog, setUseLog] = useState(false)
  const [dynamicScale, setDynamicScale] = useState(true)
  const [smoothing, setSmoothing] = useState(0) // EMA alpha in [0, 0.95]
  const xCandidatesPref = ['epoch', 'iter', 'step', 'batch', 'global_step']
  const presentCols = metrics?.columns || []
  const xCandidates = useMemo(() => xCandidatesPref.filter(k => presentCols.includes(k)), [presentCols])
  const [xAxisKey, setXAxisKey] = useState<string>(xKey)
  const loadedPersistRef = useRef(false)

  // keep xAxisKey synced to prop or available candidates
  useEffect(() => {
    if (xKey && presentCols.includes(xKey)) {
      setXAxisKey(xKey)
    } else if (!presentCols.includes(xAxisKey)) {
      // fallback to first available candidate or keep current
      const cand = xCandidates.find(Boolean)
      if (cand) setXAxisKey(cand)
    }
  }, [xKey, presentCols, xCandidates, xAxisKey])

  // load persisted controls
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

  // persist controls
  useEffect(() => {
    if (!persistKey) return
    try {
      localStorage.setItem(`MetricChart:${persistKey}` , JSON.stringify({ useLog, dynamicScale, smoothing, xAxisKey }))
    } catch {}
  }, [persistKey, useLog, dynamicScale, smoothing, xAxisKey])

  const bestTypeFor = (k: string): 'max' | 'min' | undefined => {
    const key = String(k).toLowerCase()
    if (key.includes('loss') || key.includes('error')) return 'min'
    if (key.includes('acc') || key.includes('f1') || key.includes('auc') || key.includes('map') || key.includes('precision') || key.includes('recall')) return 'max'
    return undefined
  }

  const ema = (vals: Array<number | null>, alpha: number) => {
    if (!alpha) return vals
    let s: number | null = null
    return vals.map((v) => {
      if (v == null) {
        s = null
        return null
      }
      s = s == null ? v : alpha * v + (1 - alpha) * s
      return s
    })
  }

  const option = useMemo(() => {
    const xKeyUsed = presentCols.includes(xAxisKey) ? xAxisKey : xKey
    const x = metrics.rows.map((r: any) => {
      const v = r[xKeyUsed]
      const n = v === '' || v == null ? null : Number(v)
      return n == null || Number.isNaN(n) ? null : n
    })
    // step-epoch decorations: vertical lines and alternating shading
    const canDecorateStep = xKeyUsed === 'global_step' && presentCols.includes('epoch')
    const markLines: any[] = []
    const markAreas: any[] = []
    if (canDecorateStep) {
      let prevEpoch: any = null
      let currStartIdx = 0
      const rows = metrics.rows as any[]
      for (let i = 0; i < rows.length; i++) {
        const e = rows[i]?.epoch
        if (i === 0) prevEpoch = e
        if (e !== prevEpoch) {
          // boundary at i
          const pos = x[i]
          if (pos != null) markLines.push({ xAxis: pos })
          // finish previous epoch region [currStartIdx, i-1]
          const startPos = x[currStartIdx]
          const endPos = x[Math.max(i - 1, currStartIdx)]
          if (startPos != null && endPos != null) {
            const epochIndex = Number(prevEpoch)
            if (!Number.isNaN(epochIndex) && epochIndex % 2 === 1) { // shade odd epochs
              markAreas.push([{ xAxis: startPos }, { xAxis: endPos }])
            }
          }
          currStartIdx = i
          prevEpoch = e
        }
      }
      // last epoch region
      if (rows.length) {
        const startPos = x[currStartIdx]
        const endPos = x[rows.length - 1]
        const epochIndex = Number(prevEpoch)
        if (startPos != null && endPos != null && !Number.isNaN(epochIndex) && epochIndex % 2 === 1) {
          markAreas.push([{ xAxis: startPos }, { xAxis: endPos }])
        }
      }
    }
    const series = yKeys.map((k) => {
      const rawVals: Array<number | null> = metrics.rows.map((r: any) => {
        const v = r[k] === '' || r[k] == null ? null : Number(r[k])
        const n = v == null || Number.isNaN(v) ? null : v
        if (useLog && (n == null || n <= 0)) return null
        return n
      })
      const dataVals = ema(rawVals, Math.min(0.95, Math.max(0, smoothing)))
      const bp = bestTypeFor(k)
      const s: any = {
        name: k,
        type: 'line',
        smooth: true,
        showSymbol: false,
        sampling: 'lttb',
        large: true,
        data: dataVals,
        markPoint: bp ? { data: [{ type: bp, name: bp === 'max' ? 'Best (max)' : 'Best (min)' }], symbolSize: 60 } : undefined,
      }
      if (canDecorateStep && k === yKeys[0]) {
        s.markLine = markLines.length ? { silent: true, symbol: 'none', lineStyle: { type: 'dashed', color: '#bbb' }, data: markLines } : undefined
        s.markArea = markAreas.length ? { silent: true, itemStyle: { color: 'rgba(0,0,0,0.04)' }, data: markAreas } : undefined
      }
      return s
    })
    return {
      title: { text: title },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross', label: { show: true } } },
      legend: { data: yKeys },
      xAxis: { type: 'category', data: x },
      yAxis: { type: useLog ? 'log' : 'value', scale: dynamicScale, min: dynamicScale ? 'dataMin' : 0 },
      grid: { left: 40, right: 20, top: 40, bottom: 72 },
      dataZoom: [
        { type: 'inside', throttle: 50 },
        { type: 'slider', height: 18, bottom: 36 }
      ],
      toolbox: {
        feature: {
          restore: {},
          saveAsImage: {},
        },
        right: 10
      },
      series,
    }
  }, [metrics, xKey, xAxisKey, yKeys, title, useLog, dynamicScale, smoothing, presentCols])

  const exportCsv = () => {
    try {
      const xKeyUsed = presentCols.includes(xAxisKey) ? xAxisKey : xKey
      const header = [xKeyUsed, ...yKeys]
      const lines: string[] = []
      lines.push(header.join(','))
      for (const r of metrics.rows) {
        const row: any[] = []
        const xv = r[xKeyUsed]
        row.push(xv == null ? '' : String(xv))
        for (const y of yKeys) {
          const v = r[y]
          row.push(v == null ? '' : String(v))
        }
        lines.push(row.join(','))
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
        <Tooltip title="X-axis source column (only shows if available in metrics.csv)">
          <span>
            X:&nbsp;
            <Select size="small" value={presentCols.includes(xAxisKey) ? xAxisKey : xKey} style={{ width: 140 }} onChange={setXAxisKey}
              options={(xCandidates.length ? xCandidates : [xKey]).map(k => ({ value: k, label: k }))}
            />
          </span>
        </Tooltip>
        <Button size="small" onClick={exportCsv}>Export CSV</Button>
      </Space>
      <div style={{ height: height as any, width: '100%' }}>
        <AutoResizeEChart option={option as any} group={group} />
      </div>
    </div>
  )
}
