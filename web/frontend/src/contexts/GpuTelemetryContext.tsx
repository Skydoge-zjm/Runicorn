import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { getGpuTelemetry, getGpuTelemetryHistory } from '../api'
import { useSettings } from './SettingsContext'

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

interface GpuTelemetryState {
  available: boolean | null
  reason: string
  samples: GpuSample[]
  tick: number
  /** Call on mount to start live polling */
  subscribe: () => void
  /** Call on unmount to stop live polling */
  unsubscribe: () => void
}

const GpuTelemetryContext = createContext<GpuTelemetryState | undefined>(undefined)

export function GpuTelemetryProvider({ children }: { children: ReactNode }) {
  const { settings } = useSettings()
  const [available, setAvailable] = useState<boolean | null>(null)
  const [reason, setReason] = useState('')
  const bufferRef = useRef<GpuSample[]>([])
  const [tick, setTick] = useState(0)
  const [subscribers, setSubscribers] = useState(0)

  const subscribe = useCallback(() => setSubscribers(n => n + 1), [])
  const unsubscribe = useCallback(() => setSubscribers(n => Math.max(0, n - 1)), [])

  // On app start: fetch server-side history (may contain up to 24 h of data)
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const hist = await getGpuTelemetryHistory()
        if (cancelled) return
        if (hist.samples?.length) {
          setAvailable(true)
          bufferRef.current = hist.samples as GpuSample[]
          setTick(x => x + 1)
          return
        }
        // No history — do a single probe for GPU availability
        const probe = await getGpuTelemetry()
        if (cancelled) return
        if (probe?.available) {
          setAvailable(true)
          bufferRef.current = [{ ts: probe.ts || Date.now() / 1000, gpus: probe.gpus || [] }]
          setTick(x => x + 1)
        } else {
          setAvailable(false)
          setReason(probe?.reason || '')
        }
      } catch (e: any) {
        if (!cancelled) { setAvailable(false); setReason(e?.message || '') }
      }
    })()
    return () => { cancelled = true }
  }, [])

  // Live polling — only when subscribed (component visible)
  useEffect(() => {
    if (subscribers <= 0) return
    let cancelled = false

    // Re-fetch full history to fill any gap while the page was hidden
    const syncAndPoll = async () => {
      try {
        const hist = await getGpuTelemetryHistory()
        if (cancelled) return
        if (hist.samples?.length) {
          bufferRef.current = hist.samples as GpuSample[]
          setAvailable(true)
          setTick(x => x + 1)
        }
      } catch { /* ignore, live poll will pick up */ }
    }
    syncAndPoll()

    const poll = async () => {
      try {
        const res = await getGpuTelemetry()
        if (cancelled) return
        if (!res?.available) { setAvailable(false); setReason(res?.reason || ''); return }
        setAvailable(true)
        bufferRef.current.push({ ts: res.ts || Date.now() / 1000, gpus: res.gpus || [] })
        while (bufferRef.current.length > 43200) bufferRef.current.shift()
        setTick(x => x + 1)
      } catch (e: any) {
        if (!cancelled) { setAvailable(false); setReason(e?.message || '') }
      }
    }
    const timer = setInterval(poll, (settings.refreshInterval ?? 2) * 1000)
    return () => { cancelled = true; clearInterval(timer) }
  }, [subscribers, settings.refreshInterval])

  return (
    <GpuTelemetryContext.Provider value={{ available, reason, samples: bufferRef.current, tick, subscribe, unsubscribe }}>
      {children}
    </GpuTelemetryContext.Provider>
  )
}

export function useGpuTelemetry(): GpuTelemetryState {
  const ctx = useContext(GpuTelemetryContext)
  if (!ctx) throw new Error('useGpuTelemetry must be used within GpuTelemetryProvider')
  return ctx
}
