import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { Button, Space, Switch, Tag, Tooltip, message } from 'antd'
import { useTranslation } from 'react-i18next'

function isTqdmLine(s: string) {
  // Heuristics for tqdm progress frames when redirected to file
  // e.g. " 45%|███████████▍            | 45/100 [00:12<00:15,  3.45it/s]"
  if (/\d{1,3}%\|/.test(s)) return true
  if (/it\/(s|sec)/i.test(s)) return true
  if (/ETA|elapsed/i.test(s)) return true
  return false
}

const MAX_LINES = 2000

interface LogsViewerProps {
  url: string
}

export default function LogsViewer({ url }: LogsViewerProps) {
  const { t } = useTranslation()
  
  const [allLines, setAllLines] = useState<string[]>([])
  const [autoScroll, setAutoScroll] = useState(true)
  const [filterTqdm, setFilterTqdm] = useState(true)
  const [connected, setConnected] = useState<'connected' | 'connecting' | 'disconnected'>('connecting')
  const [nextRetryMs, setNextRetryMs] = useState(0)
  
  const ref = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const retryTimer = useRef<number | null>(null)
  const backoffRef = useRef(500)
  const mountedRef = useRef(true)

  // WebSocket connection - only depends on url
  useEffect(() => {
    mountedRef.current = true
    
    const cleanup = () => {
      if (retryTimer.current) {
        window.clearTimeout(retryTimer.current)
        retryTimer.current = null
      }
      if (wsRef.current) {
        wsRef.current.onopen = null
        wsRef.current.onmessage = null
        wsRef.current.onerror = null
        wsRef.current.onclose = null
        try { wsRef.current.close() } catch {}
        wsRef.current = null
      }
    }

    const connect = () => {
      if (!mountedRef.current) return
      
      cleanup()
      setConnected('connecting')
      
      const ws = new WebSocket(url)
      wsRef.current = ws
      
      ws.onopen = () => {
        if (!mountedRef.current) return
        setConnected('connected')
        backoffRef.current = 500
        setNextRetryMs(0)
        // Clear logs on new connection - server will resend all existing logs
        setAllLines([])
      }
      
      ws.onmessage = (ev) => {
        if (!mountedRef.current) return
        const text = String(ev.data)
        setAllLines((prev) => {
          const next = [...prev, text]
          return next.length > MAX_LINES ? next.slice(-MAX_LINES) : next
        })
      }
      
      const scheduleReconnect = () => {
        if (!mountedRef.current) return
        setConnected('disconnected')
        const delay = Math.min(10000, backoffRef.current)
        backoffRef.current = Math.min(10000, Math.floor(backoffRef.current * 1.8))
        setNextRetryMs(delay)
        
        if (retryTimer.current) window.clearTimeout(retryTimer.current)
        retryTimer.current = window.setTimeout(() => {
          if (!mountedRef.current) return
          setNextRetryMs(0)
          connect()
        }, delay)
      }
      
      ws.onerror = () => scheduleReconnect()
      ws.onclose = () => scheduleReconnect()
    }

    connect()
    
    return () => {
      mountedRef.current = false
      cleanup()
    }
  }, [url])

  // Auto-scroll effect
  useEffect(() => {
    if (autoScroll && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight
    }
  }, [allLines, autoScroll])

  // Filter lines for display
  const displayLines = useMemo(() => {
    if (!filterTqdm) return allLines
    return allLines.filter(line => !isTqdmLine(line))
  }, [allLines, filterTqdm])

  const copyAll = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(displayLines.join('\n'))
      message.success(t('logs.copied'))
    } catch {
      message.error(t('logs.copy_failed'))
    }
  }, [displayLines, t])

  const clearLogs = useCallback(() => {
    setAllLines([])
  }, [])

  const statusTag = useMemo(() => {
    if (connected === 'connected') return <Tag color="green">{t('logs.status.connected')}</Tag>
    if (connected === 'connecting') return <Tag color="processing">{t('logs.status.connecting')}</Tag>
    return (
      <Tag color="default">
        {t('logs.status.disconnected')}
        {nextRetryMs ? `, ${t('logs.status.retry_in', { sec: Math.ceil(nextRetryMs/1000) })}` : ''}
      </Tag>
    )
  }, [connected, nextRetryMs, t])

  return (
    <div>
      <Space style={{ marginBottom: 8 }}>
        {statusTag}
        <Tooltip title={t('logs.tooltip.autoscroll')}>
          <span>{t('logs.autoscroll')} <Switch checked={autoScroll} onChange={setAutoScroll} style={{ marginLeft: 6 }} /></span>
        </Tooltip>
        <Tooltip title={t('logs.tooltip.filter_tqdm')}>
          <span>{t('logs.filter_tqdm')} <Switch checked={filterTqdm} onChange={setFilterTqdm} style={{ marginLeft: 6 }} /></span>
        </Tooltip>
        <Button size="small" onClick={clearLogs}>{t('logs.clear')}</Button>
        <Button size="small" onClick={copyAll}>{t('logs.copy')}</Button>
      </Space>
      <div 
        ref={ref} 
        style={{ 
          height: 320, 
          overflow: 'auto', 
          background: '#0b1020', 
          color: '#e6e9ef', 
          padding: 12, 
          borderRadius: 8, 
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', 
          fontSize: 12 
        }}
      >
        {displayLines.map((l, i) => (
          <div key={i}>{l}</div>
        ))}
      </div>
    </div>
  )
}
