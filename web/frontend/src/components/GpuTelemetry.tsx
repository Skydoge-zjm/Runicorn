import { useEffect, useMemo, useRef } from 'react'
import ReactECharts from 'echarts-for-react'
import * as echarts from 'echarts'
import { Alert, Col, Row, theme } from 'antd'
import { useTranslation } from 'react-i18next'
import { useGpuTelemetry } from '../contexts/GpuTelemetryContext'

export default function GpuTelemetry() {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const { available, reason, samples, tick, subscribe, unsubscribe } = useGpuTelemetry()

  // When background collection is off, this ensures polling runs while the component is mounted
  useEffect(() => { subscribe(); return unsubscribe }, [subscribe, unsubscribe])

  // Ref array for 4 chart instances, used for echarts.connect linkage
  const chartRefs = useRef<(ReactECharts | null)[]>([null, null, null, null])

  // Connect all 4 charts so dataZoom & legend toggle sync across them
  useEffect(() => {
    const GROUP = 'gpu-telemetry'
    const instances = chartRefs.current
      .map(r => r?.getEchartsInstance?.())
      .filter((inst): inst is echarts.ECharts => !!inst)
    if (instances.length < 2) return
    instances.forEach(inst => { inst.group = GROUP })
    echarts.connect(GROUP)
  })

  const { times, seriesUtil, seriesMem, seriesPower, seriesTemp } = useMemo(() => {
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
        sampling: 'lttb',
        large: true,
        data: samples.map(s => {
          const v = s.gpus && s.gpus[i] ? pick(s.gpus[i]) : null
          return v == null ? null : Number(v)
        })
      }))
    }
    return {
      times,
      seriesUtil: buildSeries(g => g.util_gpu),
      seriesMem: buildSeries(g => g.mem_used_pct),
      seriesPower: buildSeries(g => g.power_w),
      seriesTemp: buildSeries(g => g.temp_c),
    }
  }, [tick])

  // Theme-aware chart base options
  const textColor = token.colorText
  const subTextColor = token.colorTextSecondary
  const borderColor = token.colorBorderSecondary
  const baseGrid = { left: 48, right: 16, top: 36, bottom: 44 }

  const makeOption = (title: string, series: any[], yAxisOpts?: any) => ({
    title: { text: title, textStyle: { color: textColor, fontSize: 13, fontWeight: 600 } },
    tooltip: { trigger: 'axis' },
    legend: { data: series.map(s => s.name), textStyle: { color: subTextColor, fontSize: 11 }, top: 2, right: 8, type: 'scroll' },
    xAxis: { type: 'category', data: times, axisLabel: { color: subTextColor, fontSize: 10 }, axisLine: { lineStyle: { color: borderColor } }, splitLine: { show: false } },
    yAxis: { type: 'value', min: 0, max: 100, ...yAxisOpts, axisLabel: { color: subTextColor, fontSize: 10 }, splitLine: { lineStyle: { color: borderColor, type: 'dashed' } } },
    grid: baseGrid,
    dataZoom: [
      { type: 'inside', throttle: 50 },
      { type: 'slider', height: 14, bottom: 4, borderColor: 'transparent', backgroundColor: borderColor + '33',
        fillerColor: token.colorPrimary + '22', handleSize: '60%',
        start: Math.max(0, 100 - (times.length > 0 ? 300 / times.length * 100 : 100)), end: 100 },
    ],
    series,
  })

  const optUtil = useMemo(() => makeOption(t('gpu.chart.util'), seriesUtil), [times, seriesUtil, t, textColor, subTextColor, borderColor])
  const optMem = useMemo(() => makeOption(t('gpu.chart.mem'), seriesMem), [times, seriesMem, t, textColor, subTextColor, borderColor])
  const optPower = useMemo(() => makeOption(t('gpu.chart.power'), seriesPower, { min: 'dataMin', max: undefined, scale: true }), [times, seriesPower, t, textColor, subTextColor, borderColor])
  const optTemp = useMemo(() => makeOption(t('gpu.chart.temp'), seriesTemp, { min: 'dataMin', max: undefined, scale: true }), [times, seriesTemp, t, textColor, subTextColor, borderColor])

  if (available === false) {
    return <Alert type="warning" showIcon message={t('gpu.not_available')} description={reason || undefined} />
  }

  const chartStyle = { height: 220, width: '100%' }
  const cellStyle: React.CSSProperties = {
    border: `1px solid ${borderColor}`,
    borderRadius: 8,
    padding: '8px 4px 0',
    background: token.colorBgContainer,
  }

  return (
    <div>
      <Row gutter={[12, 12]}>
        <Col xs={24} md={12}>
          <div style={cellStyle}>
            <ReactECharts ref={el => { chartRefs.current[0] = el }} option={optUtil as any} style={chartStyle} />
          </div>
        </Col>
        <Col xs={24} md={12}>
          <div style={cellStyle}>
            <ReactECharts ref={el => { chartRefs.current[1] = el }} option={optMem as any} style={chartStyle} />
          </div>
        </Col>
        <Col xs={24} md={12}>
          <div style={cellStyle}>
            <ReactECharts ref={el => { chartRefs.current[2] = el }} option={optPower as any} style={chartStyle} />
          </div>
        </Col>
        <Col xs={24} md={12}>
          <div style={cellStyle}>
            <ReactECharts ref={el => { chartRefs.current[3] = el }} option={optTemp as any} style={chartStyle} />
          </div>
        </Col>
      </Row>
    </div>
  )
}
