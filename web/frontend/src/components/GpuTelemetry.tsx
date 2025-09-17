import React, { useEffect, useMemo, useRef, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { Alert, Space, Switch, Typography, Collapse } from 'antd'
import { ThunderboltOutlined, DashboardOutlined, DatabaseOutlined, FireOutlined } from '@ant-design/icons'
import { getGpuTelemetry } from '../api'
import { useTranslation } from 'react-i18next'

interface GpuSample {
  ts: number
  gpus: Array<{
    index: number
    name: string
    util_gpu?: number
    mem_used_pct?: number
    power_w?: number
    power_limit_w?: number
    temp_c?: number
  }>
}

const MAX_POINTS = 120 // keep last 120 samples

export default function GpuTelemetry() {
  const { t } = useTranslation()
  const [available, setAvailable] = useState<boolean | null>(null)
  const [reason, setReason] = useState<string>('')
  const [paused, setPaused] = useState(false)
  const bufferRef = useRef<GpuSample[]>([])
  const [tick, setTick] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const [activeKeys, setActiveKeys] = useState<string[]>([])

  useEffect(() => {
    let timer: any
    const poll = async () => {
      if (paused) return
      try {
        const res = await getGpuTelemetry()
        if (!res?.available) {
          setAvailable(false)
          setReason(res?.reason || t('gpu.not_available'))
          return
        }
        setAvailable(true)
        const sample: GpuSample = { ts: res.ts || Date.now() / 1000, gpus: res.gpus || [] }
        const arr = bufferRef.current.slice()
        arr.push(sample)
        while (arr.length > MAX_POINTS) arr.shift()
        bufferRef.current = arr
        setTick((x) => x + 1)
      } catch (e: any) {
        setAvailable(false)
        setReason(e?.message || t('gpu.not_available'))
      }
    }
    // immediate fetch, then interval
    poll()
    timer = setInterval(poll, 2000)
    return () => clearInterval(timer)
  }, [paused])

  const { times, gpuNames, seriesUtil, seriesMem, seriesPower, seriesTemp } = useMemo(() => {
    const samples = bufferRef.current
    const times = samples.map(s => new Date((s.ts || 0) * 1000).toLocaleTimeString())
    const maxGpuCount = samples.reduce((m, s) => Math.max(m, s.gpus?.length || 0), 0)
    const gpuNames: string[] = []
    for (let i = 0; i < maxGpuCount; i++) {
      const first = samples.find(s => s.gpus && s.gpus[i])
      gpuNames.push(first ? `GPU${first.gpus[i].index} ${first.gpus[i].name}` : `GPU${i}`)
    }
    const buildSeries = (pick: (g: any) => number | null | undefined) => {
      return new Array(maxGpuCount).fill(0).map((_, i) => ({
        name: gpuNames[i] || `GPU${i}`,
        type: 'line' as const,
        smooth: true,
        showSymbol: false,
        connectNulls: true,
        data: samples.map(s => {
          const v = s.gpus && s.gpus[i] ? pick(s.gpus[i]) : null
          return v == null ? null : Number(v)
        })
      }))
    }
    const seriesUtil = buildSeries(g => g.util_gpu)
    const seriesMem = buildSeries(g => g.mem_used_pct)
    const seriesPower = buildSeries(g => g.power_w)
    const seriesTemp = buildSeries(g => g.temp_c)
    return { times, gpuNames, seriesUtil, seriesMem, seriesPower, seriesTemp }
  }, [tick])

  const summary = useMemo(() => {
    const last = bufferRef.current[bufferRef.current.length - 1]
    const res = { utilAvg: 0, memAvg: 0, powerNow: 0, powerMax: 0, tempMax: 0 }
    if (!last || !last.gpus || last.gpus.length === 0) return res
    const g = last.gpus
    const n = g.length
    const sum = (arr: number[]) => arr.reduce((a, b) => a + (Number.isFinite(b) ? b : 0), 0)
    const vals = {
      util: g.map(x => Number(x.util_gpu ?? 0)),
      mem: g.map(x => Number(x.mem_used_pct ?? 0)),
      pwr: g.map(x => Number(x.power_w ?? 0)),
      pmax: g.map(x => Number(x.power_limit_w ?? 0)),
      temp: g.map(x => Number(x.temp_c ?? 0)),
    }
    res.utilAvg = Math.round(sum(vals.util) / n)
    res.memAvg = Math.round(sum(vals.mem) / n)
    res.powerNow = Math.round(sum(vals.pwr))
    res.powerMax = Math.round(sum(vals.pmax))
    res.tempMax = Math.max(...vals.temp)
    return res
  }, [tick])

  const baseGrid = { left: 48, right: 16, top: 40, bottom: 40 }

  const optUtil = useMemo(() => ({
    title: { text: t('gpu.chart.util') },
    tooltip: { trigger: 'axis' },
    legend: { data: seriesUtil.map(s => s.name) },
    xAxis: { type: 'category', data: times },
    yAxis: { type: 'value', min: 0, max: 100 },
    grid: baseGrid,
    dataZoom: [ { type: 'inside', throttle: 50 }, { type: 'slider', height: 18, bottom: 8 } ],
    series: seriesUtil,
  }), [times, seriesUtil, t])

  const optMem = useMemo(() => ({
    title: { text: t('gpu.chart.mem') },
    tooltip: { trigger: 'axis' },
    legend: { data: seriesMem.map(s => s.name) },
    xAxis: { type: 'category', data: times },
    yAxis: { type: 'value', min: 0, max: 100 },
    grid: baseGrid,
    dataZoom: [ { type: 'inside', throttle: 50 }, { type: 'slider', height: 18, bottom: 8 } ],
    series: seriesMem,
  }), [times, seriesMem, t])

  const optPower = useMemo(() => ({
    title: { text: t('gpu.chart.power') },
    tooltip: { trigger: 'axis' },
    legend: { data: seriesPower.map(s => s.name) },
    xAxis: { type: 'category', data: times },
    yAxis: { type: 'value', min: 'dataMin', scale: true },
    grid: baseGrid,
    dataZoom: [ { type: 'inside', throttle: 50 }, { type: 'slider', height: 18, bottom: 8 } ],
    series: seriesPower,
  }), [times, seriesPower, t])

  const optTemp = useMemo(() => ({
    title: { text: t('gpu.chart.temp') },
    tooltip: { trigger: 'axis' },
    legend: { data: seriesTemp.map(s => s.name) },
    xAxis: { type: 'category', data: times },
    yAxis: { type: 'value', min: 'dataMin', scale: true },
    grid: baseGrid,
    dataZoom: [ { type: 'inside', throttle: 50 }, { type: 'slider', height: 18, bottom: 8 } ],
    series: seriesTemp,
  }), [times, seriesTemp, t])

  if (available === false) {
    return <Alert type="warning" showIcon message={t('gpu.not_available')} description={reason || undefined} />
  }

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <Space align="center" style={{ marginBottom: 8 }}>
        <Typography.Text type="secondary">{t('polling.every2s')}</Typography.Text>
        <span style={{ marginLeft: 12 }}>{t('pause')} <Switch checked={paused} onChange={setPaused} /></span>
      </Space>

      <Collapse
        activeKey={activeKeys}
        onChange={(k) => {
          setActiveKeys(k as string[])
          setTimeout(() => { try { window.dispatchEvent(new Event('resize')) } catch {} }, 350)
        }}
        items={[
          { key: 'util', label: t('gpu.chart.util'), children: (
            <ReactECharts option={optUtil as any} style={{ height: 260, width: '100%' }} />
          ) },
          { key: 'mem', label: t('gpu.chart.mem'), children: (
            <ReactECharts option={optMem as any} style={{ height: 260, width: '100%' }} />
          ) },
          { key: 'power', label: t('gpu.chart.power'), children: (
            <ReactECharts option={optPower as any} style={{ height: 260, width: '100%' }} />
          ) },
          { key: 'temp', label: t('gpu.chart.temp'), children: (
            <ReactECharts option={optTemp as any} style={{ height: 260, width: '100%' }} />
          ) },
        ]}
      />

      {/* Static compact badges when panels are collapsed */}
      {available && (activeKeys.indexOf('power') === -1) && (
        <div style={{ position: 'absolute', right: 12, top: 12, background: 'rgba(0,0,0,0.55)', color: '#fff', borderRadius: 8, padding: '4px 8px', pointerEvents: 'none' }}>
          <ThunderboltOutlined style={{ marginRight: 6 }} />{t('gpu.power')} {summary.powerNow}{summary.powerMax ? `/${summary.powerMax}` : ''} W
        </div>
      )}
      {available && (activeKeys.indexOf('util') === -1) && (
        <div style={{ position: 'absolute', right: 12, top: 44, background: 'rgba(0,0,0,0.55)', color: '#fff', borderRadius: 8, padding: '4px 8px', pointerEvents: 'none' }}>
          <DashboardOutlined style={{ marginRight: 6 }} />{t('gpu.util')} {summary.utilAvg}%
        </div>
      )}
      {available && (activeKeys.indexOf('mem') === -1) && (
        <div style={{ position: 'absolute', right: 12, top: 76, background: 'rgba(0,0,0,0.55)', color: '#fff', borderRadius: 8, padding: '4px 8px', pointerEvents: 'none' }}>
          <DatabaseOutlined style={{ marginRight: 6 }} />{t('gpu.mem')} {summary.memAvg}%
        </div>
      )}
      {available && (activeKeys.indexOf('temp') === -1) && (
        <div style={{ position: 'absolute', right: 12, top: 108, background: 'rgba(0,0,0,0.55)', color: '#fff', borderRadius: 8, padding: '4px 8px', pointerEvents: 'none' }}>
          <FireOutlined style={{ marginRight: 6 }} />{t('gpu.temp')} {summary.tempMax}°C
        </div>
      )}
    </div>
  )
}
