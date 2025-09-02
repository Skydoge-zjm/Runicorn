import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Card, Descriptions, Space, Progress, Alert, Typography, Collapse, Popover, Tag } from 'antd'
import { ThunderboltOutlined, DashboardOutlined, DatabaseOutlined, FireOutlined, ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons'
import { getRunDetail, getMetrics, getStepMetrics, getProgress, getGpuTelemetry } from '../api'
import LogsViewer from '../components/LogsViewer'
import MetricChart from '../components/MetricChart'
import GpuTelemetry from '../components/GpuTelemetry'

export default function RunDetailPage() {
  const { id = '' } = useParams()
  const [detail, setDetail] = useState<any>(null)
  const [metrics, setMetrics] = useState<{ columns: string[]; rows: any[] }>({ columns: [], rows: [] })
  const [stepMetrics, setStepMetrics] = useState<{ columns: string[]; rows: any[] }>({ columns: [], rows: [] })
  const [prog, setProg] = useState<any>(null)
  const [gpu, setGpu] = useState<{ util: number; mem: number; power: number; temp: number; gpus?: any[] } | null>(null)
  const gpuHistRef = useRef<Array<{ t: number; util: number; mem: number; power: number; temp: number }>>([])
  const prevEpochRef = useRef<{ t: number; percent: number } | null>(null)
  const prevIterRef = useRef<{ t: number; step: number } | null>(null)
  const [etaEpochSec, setEtaEpochSec] = useState<number | null>(null)
  const [etaIterSec, setEtaIterSec] = useState<number | null>(null)

  const loadDetail = async () => setDetail(await getRunDetail(id))
  const loadMetrics = async () => setMetrics(await getMetrics(id))
  const loadStepMetrics = async () => setStepMetrics(await getStepMetrics(id))

  useEffect(() => {
    loadDetail()
    loadMetrics()
    loadStepMetrics()
    const loadProg = async () => {
      try { setProg(await getProgress(id)) } catch {}
    }
    loadProg()
    const t = setInterval(() => {
      loadDetail();
      loadMetrics();
      loadStepMetrics();
      loadProg();
    }, 3000)
    return () => clearInterval(t)
  }, [id])

  // progress estimation using last epoch and saved total epochs
  const totalEpochs = useMemo(() => {
    try {
      const raw = localStorage.getItem(`run_meta_${id}`)
      if (!raw) return undefined
      const meta = JSON.parse(raw)
      return Number(meta?.epochs) || undefined
    } catch { return undefined }
  }, [id])
  const lastEpoch = useMemo(() => {
    const n = metrics.rows.length
    if (!n) return 0
    const v = Number(metrics.rows[n - 1]?.epoch)
    return Number.isFinite(v) ? v : 0
  }, [metrics])
  const percent = useMemo(() => {
    if (!totalEpochs || totalEpochs <= 0) return undefined
    const p = Math.max(0, Math.min(100, Math.round((lastEpoch / totalEpochs) * 100)))
    return p
  }, [lastEpoch, totalEpochs])

  const iterPercent = useMemo(() => {
    if (!prog || !prog.available) return undefined
    if (prog?.percent != null) return Math.max(0, Math.min(100, Number(prog.percent)))
    const step = Number(prog?.step)
    const total = Number(prog?.total)
    if (!Number.isFinite(step) || !Number.isFinite(total) || total <= 0) return undefined
    return Math.max(0, Math.min(100, Math.round((step / total) * 100)))
  }, [prog])

  // ETA calculations
  useEffect(() => {
    const now = Date.now() / 1000
    // Epoch ETA based on percent speed
    if (percent != null) {
      const prev = prevEpochRef.current
      if (prev && percent > prev.percent) {
        const dp = percent - prev.percent
        const dt = now - prev.t
        if (dt > 0) {
          const speed = dp / dt // percent per second
          if (speed > 1e-6) setEtaEpochSec(Math.max(0, Math.round((100 - percent) / speed)))
        }
      }
      prevEpochRef.current = { t: now, percent }
    }
    // Iter ETA based on steps/sec
    const step = Number(prog?.step)
    const total = Number(prog?.total)
    if (Number.isFinite(step) && Number.isFinite(total) && total > 0) {
      const prev = prevIterRef.current
      if (prev && step > prev.step) {
        const ds = step - prev.step
        const dt = now - prev.t
        if (dt > 0) {
          const sps = ds / dt
          if (sps > 1e-6) setEtaIterSec(Math.max(0, Math.round((total - step) / sps)))
        }
      }
      prevIterRef.current = { t: now, step }
    }
  }, [percent, prog])

  const formatETA = (secs: number | null) => {
    if (secs == null) return '-'
    const s = Math.max(0, Math.round(secs))
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    const ss = s % 60
    if (h > 0) return `${h}h ${m}m ${ss}s`
    if (m > 0) return `${m}m ${ss}s`
    return `${ss}s`
  }

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
        {percent != null ? (
          <div>
            <Typography.Text strong>Overall progress (epochs)</Typography.Text>
            <Progress percent={percent} status={detail?.status === 'running' ? 'active' : 'normal'} />
            <div style={{ fontSize: 12, color: '#888' }}>ETA: {formatETA(etaEpochSec)}</div>
          </div>
        ) : (
          <Alert type="info" showIcon message="Overall progress will appear after first epoch. To enable %, keep this tab open when starting the run so we can store the total epochs." />
        )}
        {iterPercent != null && (
          <div>
            <div style={{ height: 8 }} />
            <Typography.Text strong>Current epoch progress (iter)</Typography.Text>
            <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
              Phase: {prog?.phase || '-'} · Step: {prog?.step ?? '-'} / {prog?.total ?? '-'}
            </div>
            <Progress percent={iterPercent} status={detail?.status === 'running' ? 'active' : 'normal'} strokeColor="#52c41a" />
            <div style={{ fontSize: 12, color: '#888' }}>ETA: {formatETA(etaIterSec)}</div>
          </div>
        )}
      </Card>

      <Card title="Training Curves">
        <Collapse
          defaultActiveKey={["loss", "acc"]}
          items={[
            { key: 'loss', label: 'Loss', children: (
                <MetricChart metrics={metrics} xKey="epoch" yKeys={["train_loss", "val_loss"]} title="Loss" height={360}
                  group={`epoch-group-${id}`} persistKey={`run:${id}:epoch:loss`} />
            ) },
            { key: 'acc', label: 'Accuracy', children: (
                <MetricChart metrics={metrics} xKey="epoch" yKeys={["train_acc_top1", "val_acc_top1", "best_val_acc_top1"]} title="Accuracy" height={360}
                  group={`epoch-group-${id}`} persistKey={`run:${id}:epoch:acc`} />
            ) },
            ...(stepMetrics.columns.length ? [
              { key: 'step_loss', label: 'Step Loss', children: (
                  <MetricChart metrics={stepMetrics} xKey="global_step" yKeys={["train_loss"]} title="Step Loss" height={360}
                    group={`step-group-${id}`} persistKey={`run:${id}:step:loss`} />
              ) },
              { key: 'step_acc', label: 'Step Accuracy', children: (
                  <MetricChart metrics={stepMetrics} xKey="global_step" yKeys={["train_acc_top1"]} title="Step Accuracy (Top1)" height={360}
                    group={`step-group-${id}`} persistKey={`run:${id}:step:acc`} />
              ) },
            ] : [])
          ]}
        />
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
