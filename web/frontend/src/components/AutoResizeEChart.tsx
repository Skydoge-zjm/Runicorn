import React, { useEffect, useMemo, useRef } from 'react'
import ReactECharts, { EChartsReactProps } from 'echarts-for-react'
import * as echarts from 'echarts'

export default function AutoResizeEChart(props: EChartsReactProps & { group?: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ReactECharts>(null as any)

  useEffect(() => {
    if (!containerRef.current) return
    const el = containerRef.current
    let rafId: number | null = null

    const resize = () => {
      if (rafId != null) cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(() => {
        try { (chartRef.current as any)?.getEchartsInstance()?.resize?.() } catch {}
      })
    }

    // Observe container size changes if supported
    let ro: any = null
    const RO = (window as any).ResizeObserver
    if (RO) {
      ro = new RO(() => resize())
      ro.observe(el)
    }

    // Also listen to window resize as a fallback
    window.addEventListener('resize', resize)
    return () => {
      window.removeEventListener('resize', resize)
      ro && ro.disconnect()
      if (rafId != null) cancelAnimationFrame(rafId)
    }
  }, [])

  // connect charts by group id for linked zoom/tooltip/axisPointer
  useEffect(() => {
    const inst = (chartRef.current as any)?.getEchartsInstance?.()
    if (!inst) return
    if (props.group) {
      try {
        ;(inst as any).group = props.group
        echarts.connect(props.group)
      } catch {}
    }
  }, [props.group])

  // Ensure the chart takes full size of its container
  const style = useMemo(() => ({ width: '100%', height: '100%', ...(props.style || {}) }), [props.style])
  const { group, style: _ignoredStyle, ...rest } = props as any

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%' }}>
      {/* @ts-ignore */}
      <ReactECharts ref={chartRef as any} {...rest} style={style} />
    </div>
  )
}
