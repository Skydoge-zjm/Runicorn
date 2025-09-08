import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Card, Descriptions, Space, Alert, Popover, Tag, Switch, Select, Button } from 'antd'
import { ThunderboltOutlined, DashboardOutlined, DatabaseOutlined, FireOutlined, ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons'
import { getRunDetail, getStepMetrics, getGpuTelemetry, listRunsByName } from '../api'
import LogsViewer from '../components/LogsViewer'
import MetricChart from '../components/MetricChart'
import GpuTelemetry from '../components/GpuTelemetry'
import MultiRunMetricChart from '../components/MultiRunMetricChart'

export default function RunDetailPage() {
  const { id = '' } = useParams()
  const [detail, setDetail] = useState<any>(null)
  const [stepMetrics, setStepMetrics] = useState<{ columns: string[]; rows: any[] }>({ columns: [], rows: [] })
  const [stepXAxis, setStepXAxis] = useState<'global_step' | 'time'>(() => {
    try { return (localStorage.getItem(`run:${id}:step:xAxis`) as any) || 'global_step' } catch { return 'global_step' }
  })
  const [twoCol, setTwoCol] = useState<boolean>(() => {
    try { return localStorage.getItem(`run:${id}:layout:twoCol`) === '1' } catch { return true }
  })
  const [gpu, setGpu] = useState<{ util: number; mem: number; power: number; temp: number; gpus?: any[] } | null>(null)
  const gpuHistRef = useRef<Array<{ t: number; util: number; mem: number; power: number; temp: number }>>([])

  // Compare runs (same experiment name) state
  const [runsUnderName, setRunsUnderName] = useState<any[]>([])
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([])
  const [overlayKeys, setOverlayKeys] = useState<string[]>([])
  const [overlayMetricsMap, setOverlayMetricsMap] = useState<Record<string, { columns: string[]; rows: any[] }>>({})

  const loadDetail = async () => setDetail(await getRunDetail(id))
  const loadStepMetrics = async () => setStepMetrics(await getStepMetrics(id))

  useEffect(() => {
    loadDetail()
    loadStepMetrics()
    const t = setInterval(() => {
      loadDetail();
      loadStepMetrics();
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

  const gridStyle: React.CSSProperties = useMemo(() => ({
    display: 'grid',
    gridTemplateColumns: twoCol ? '1fr 1fr' : '1fr',
    gap: 16,
  }), [twoCol])

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title={`Run ${id}`}>
        <Descriptions
          bordered
          size="small"
          column={1}
          items={[
            { key: 'status', label: 'Status', children: detail?.status || '-' },
            { key: 'pid', label: 'PID', children: detail?.pid || '-' },
            { key: 'project', label: 'Project', children: detail?.project || '-' },
            { key: 'name', label: 'Name', children: detail?.name || '-' },
            { key: 'run_dir', label: 'Run Dir', children: detail?.run_dir || '-' },
            { key: 'logs', label: 'Logs', children: detail?.logs || '-' },
            { key: 'metrics', label: 'Metrics Events', children: detail?.metrics || '-' },
          ]}
        />
        <div style={{ height: 12 }} />
        <div style={{ marginBottom: 8 }}>
          <Space size="large" wrap>
            <span><DashboardOutlined style={{ marginRight: 6 }} />利用率 {gpu?.util ?? '-'}% {trendIcon('util')}</span>
            <span><DatabaseOutlined style={{ marginRight: 6 }} />显存 {gpu?.mem ?? '-'}% {trendIcon('mem')}</span>
            <span><ThunderboltOutlined style={{ marginRight: 6 }} />功耗 {gpu?.power ?? '-'} W {trendIcon('power')}</span>
            <span><FireOutlined style={{ marginRight: 6 }} />温度 {gpu?.temp ?? '-'}°C {trendIcon('temp')}</span>
            {gpu?.gpus && (
              <Popover
                placement="bottom"
                content={(
                  <div style={{ minWidth: 220 }}>
                    {gpu.gpus.map((x: any, i: number) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>GPU{x.index} {x.name}</span>
                        <span style={{ color: '#555' }}>{Math.round(x.util_gpu ?? 0)}% · {Math.round(x.mem_used_pct ?? 0)}% · {Math.round(x.power_w ?? 0)}W · {Math.round(x.temp_c ?? 0)}°C</span>
                      </div>
                    ))}
                  </div>
                )}
              >
                <Tag color="blue" style={{ cursor: 'pointer' }}>GPUs: {gpu.gpus.length}</Tag>
              </Popover>
            )}
          </Space>
        </div>
      </Card>

      <Card title="Compare Runs (Same Experiment)">
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Space wrap>
            <span>
              Runs:&nbsp;
              <Select
                mode="multiple"
                allowClear
                value={selectedRunIds}
                onChange={setSelectedRunIds as any}
                placeholder="Select runs to overlay"
                style={{ minWidth: 360 }}
                options={(runsUnderName || []).map((r: any) => ({ value: r.id, label: r.id }))}
              />
            </span>
            <span>
              Metrics:&nbsp;
              <Select
                mode="multiple"
                allowClear
                value={overlayKeys}
                onChange={setOverlayKeys as any}
                placeholder="Select metric keys"
                style={{ minWidth: 300 }}
                options={overlayMetricCandidates.map(k => ({ value: k, label: k }))}
              />
            </span>
            <span>Step X: <Select size="small" value={stepXAxis} onChange={v => setStepXAxis(v as any)} style={{ width: 140 }} options={[
              { value: 'global_step', label: 'global_step' },
              { value: 'time', label: 'time' },
            ]} /></span>
            <Button size="small" onClick={async () => {
              const next: Record<string, { columns: string[]; rows: any[] }> = {}
              for (const rid of selectedRunIds) {
                try { next[rid] = await getStepMetrics(rid) } catch {}
              }
              setOverlayMetricsMap(next)
            }}>Refresh</Button>
          </Space>

          {overlayKeys.length === 0 || selectedRunIds.length === 0 ? (
            <Alert type="info" showIcon message="Select one or more runs and metrics to overlay." />
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: twoCol ? '1fr 1fr' : '1fr', gap: 16 }}>
              {overlayKeys.map((k) => (
                <MultiRunMetricChart
                  key={k}
                  title={k}
                  xKey={stepXAxis}
                  yKey={k}
                  runs={selectedRunIds.map((rid) => ({ id: rid, metrics: overlayMetricsMap[rid] || { columns: [], rows: [] } }))}
                  height={300}
                  group={`overlay-group-${id}`}
                  persistKey={`run:${id}:overlay:${k}`}
                />
              ))}
            </div>
          )}
        </Space>
      </Card>

      <Card title="Metrics" extra={(
        <Space>
          <span>Two Columns <Switch checked={twoCol} onChange={setTwoCol} /></span>
          <span>Step X: <Select size="small" value={stepXAxis} onChange={v => setStepXAxis(v as any)} style={{ width: 140 }} options={[
            { value: 'global_step', label: 'global_step' },
            { value: 'time', label: 'time' },
          ]} /></span>
        </Space>
      )}>
        {stepMetricKeys.length === 0 ? (
          <Alert type="info" showIcon message="No step metrics yet." />
        ) : (
          <div style={gridStyle}>
            {stepMetricKeys.map((k) => (
              <MetricChart key={k} metrics={stepMetrics} xKey={stepXAxis} yKeys={[k]} title={k} height={300}
                group={`step-group-${id}`} persistKey={`run:${id}:step:${k}`} />
            ))}
          </div>
        )}
      </Card>

      <Card title="GPU Telemetry">
        <GpuTelemetry />
      </Card>

      <Card title="Live Logs">
        <LogsViewer url={logUrl} persistKey={`run_${id}_logs`} />
      </Card>
    </Space>
  )
}
