import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Space, Switch, Tag, Tooltip, message } from 'antd'

function isTqdmLine(s: string) {
  // Heuristics for tqdm progress frames when redirected to file
  // e.g. " 45%|███████████▍            | 45/100 [00:12<00:15,  3.45it/s]"
  if (/\d{1,3}%\|/.test(s)) return true
  if (/it\/(s|sec)/i.test(s)) return true
  if (/ETA|elapsed/i.test(s)) return true
  return false
}

export default function LogsViewer({ url, persistKey }: { url: string, persistKey?: string }) {
  const [lines, setLines] = useState<string[]>(() => {
    if (!persistKey) return []
    try {
      const raw = localStorage.getItem(persistKey)
      if (!raw) return []
      const arr = JSON.parse(raw)
      return Array.isArray(arr) ? arr.slice(-2000) : []
    } catch { return [] }
  })
  const [autoScroll, setAutoScroll] = useState(true)
  const [filterTqdm, setFilterTqdm] = useState(true)
  const [connected, setConnected] = useState<'connected' | 'connecting' | 'disconnected'>('connecting')
  const [nextRetryMs, setNextRetryMs] = useState(0)
  const ref = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const retryTimer = useRef<number | null>(null)
  const backoffRef = useRef(500)

  useEffect(() => {
    let closedByUser = false

    const connect = () => {
      try { if (wsRef.current) wsRef.current.close() } catch {}
      setConnected('connecting')
      const ws = new WebSocket(url)
      wsRef.current = ws
      ws.onopen = () => {
        setConnected('connected')
        backoffRef.current = 500
        setNextRetryMs(0)
      }
      ws.onmessage = (ev) => {
        const text = String(ev.data)
        if (filterTqdm && isTqdmLine(text)) return
        setLines((prev) => {
          const next = [...prev, text]
          const sliced = next.slice(-2000)
          try { if (persistKey) localStorage.setItem(persistKey, JSON.stringify(sliced)) } catch {}
          return sliced
        })
      }
      const scheduleReconnect = () => {
        if (closedByUser) return
        setConnected('disconnected')
        const delay = Math.min(10000, backoffRef.current)
        backoffRef.current = Math.min(10000, Math.floor(backoffRef.current * 1.8))
        setNextRetryMs(delay)
        if (retryTimer.current) window.clearTimeout(retryTimer.current)
        retryTimer.current = window.setTimeout(() => {
          setNextRetryMs(0)
          connect()
        }, delay)
      }
      ws.onerror = scheduleReconnect
      ws.onclose = scheduleReconnect
    }

    connect()
    return () => {
      closedByUser = true
      try { wsRef.current?.close() } catch {}
      if (retryTimer.current) window.clearTimeout(retryTimer.current)
    }
  }, [url, filterTqdm, persistKey])

  useEffect(() => {
    if (autoScroll && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight
    }
  }, [lines, autoScroll])

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(lines.join('\n'))
      message.success('Copied logs to clipboard')
    } catch {
      message.error('Copy failed')
    }
  }

  const statusTag = useMemo(() => {
    if (connected === 'connected') return <Tag color="green">Connected</Tag>
    if (connected === 'connecting') return <Tag color="processing">Connecting...</Tag>
    return <Tag color="default">Disconnected{nextRetryMs ? `, retry in ${Math.ceil(nextRetryMs/1000)}s` : ''}</Tag>
  }, [connected, nextRetryMs])

  return (
    <div>
      <Space style={{ marginBottom: 8 }}>
        {statusTag}
        <Tooltip title="Automatically scroll to the latest line">
          <span>Auto Scroll <Switch checked={autoScroll} onChange={setAutoScroll} style={{ marginLeft: 6 }} /></span>
        </Tooltip>
        <Tooltip title="Hide tqdm progress frames to reduce noise">
          <span>Filter tqdm <Switch checked={filterTqdm} onChange={setFilterTqdm} style={{ marginLeft: 6 }} /></span>
        </Tooltip>
        <Button size="small" onClick={() => { setLines([]); try { if (persistKey) localStorage.removeItem(persistKey) } catch {} }}>Clear</Button>
        <Button size="small" onClick={copyAll}>Copy</Button>
      </Space>
      <div ref={ref} style={{ height: 320, overflow: 'auto', background: '#0b1020', color: '#e6e9ef', padding: 12, borderRadius: 8, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
        {lines.map((l, i) => (
          <div key={i}>{l}</div>
        ))}
      </div>
    </div>
  )
}
