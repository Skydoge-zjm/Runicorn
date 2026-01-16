import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { Button, Input, Space, Switch, Tag, Tooltip, message } from 'antd'
import { useTranslation } from 'react-i18next'
import AnsiToHtml from 'ansi-to-html'

// Constants
const MAX_LINES = 5000
const RECONNECT_BASE_MS = 500
const RECONNECT_MAX_MS = 10000

/**
 * Escape HTML special characters to prevent XSS attacks.
 * Used for search keyword highlighting.
 */
function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

/**
 * Escape special regex characters in a string.
 */
function escapeRegex(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// ANSI converter instance with terminal-like colors
const ansiConverter = new AnsiToHtml({
  fg: '#e6e9ef',
  bg: '#0b1020',
  newline: false,
  escapeXML: true,
  colors: {
    0: '#1d1f21',   // black
    1: '#cc6666',   // red
    2: '#b5bd68',   // green
    3: '#f0c674',   // yellow
    4: '#81a2be',   // blue
    5: '#b294bb',   // magenta
    6: '#8abeb7',   // cyan
    7: '#c5c8c6',   // white
  },
})

/**
 * Heuristics for detecting tqdm progress bar lines.
 * Only matches actual tqdm-style progress bars, not MetricLogger output.
 */
function isTqdmLine(s: string): boolean {
  // tqdm progress bar pattern: " 45%|███████████▍            | 45/100 [00:12<00:15,  3.45it/s]"
  // Must have percentage + bar character (█ or #) pattern
  if (/\d{1,3}%\|[█▏▎▍▌▋▊▉#\-\s]+\|/.test(s)) return true
  
  // Alternative tqdm pattern with brackets: "100%|██████████| 100/100 [00:10<00:00, 10.00it/s]"
  if (/\d{1,3}%\|.*\|\s*\d+\/\d+\s*\[/.test(s)) return true
  
  // Simple tqdm without bar: "  5%|          | 5/100 [00:01<00:19,  4.89it/s]"
  if (/^\s*\d{1,3}%\|/.test(s)) return true
  
  return false
}

interface LogsViewerProps {
  url: string
}

export default function LogsViewer({ url }: LogsViewerProps) {
  const { t } = useTranslation()
  
  const [allLines, setAllLines] = useState<string[]>([])
  const [autoScroll, setAutoScroll] = useState(true)
  const [filterTqdm, setFilterTqdm] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [connected, setConnected] = useState<'connected' | 'connecting' | 'disconnected'>('connecting')
  const [nextRetryMs, setNextRetryMs] = useState(0)
  
  const containerRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const retryTimer = useRef<number | null>(null)
  const backoffRef = useRef(RECONNECT_BASE_MS)
  const mountedRef = useRef(true)

  // WebSocket connection with exponential backoff
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
        backoffRef.current = RECONNECT_BASE_MS
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
        const delay = Math.min(RECONNECT_MAX_MS, backoffRef.current)
        backoffRef.current = Math.min(RECONNECT_MAX_MS, Math.floor(backoffRef.current * 1.8))
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
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [allLines, autoScroll])

  // Filter and search lines
  const displayLines = useMemo(() => {
    let lines = allLines
    
    if (filterTqdm) {
      lines = lines.filter(line => !isTqdmLine(line))
    }
    
    if (searchKeyword) {
      const keyword = searchKeyword.toLowerCase()
      lines = lines.filter(line => line.toLowerCase().includes(keyword))
    }
    
    return lines
  }, [allLines, filterTqdm, searchKeyword])

  // Render line with ANSI colors and search highlight
  const renderLine = useCallback((line: string, index: number) => {
    let html: string
    try {
      html = ansiConverter.toHtml(line)
    } catch {
      // Fallback to escaped plain text if ANSI conversion fails
      html = escapeHtml(line)
    }
    
    // Highlight search keyword (with proper HTML escaping to prevent XSS)
    if (searchKeyword) {
      const regex = new RegExp(`(${escapeRegex(searchKeyword)})`, 'gi')
      html = html.replace(regex, '<mark style="background:#f0c674;color:#1d1f21">$1</mark>')
    }
    
    return (
      <div 
        key={index} 
        className="log-line"
        style={{ display: 'flex', minHeight: 20 }}
      >
        <span style={{ 
          color: '#6c7a89', 
          minWidth: 50, 
          textAlign: 'right', 
          paddingRight: 12,
          userSelect: 'none',
          flexShrink: 0,
        }}>
          {index + 1}
        </span>
        <span 
          style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}
          dangerouslySetInnerHTML={{ __html: html }} 
        />
      </div>
    )
  }, [searchKeyword])

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
      <Space style={{ marginBottom: 8 }} wrap>
        {statusTag}
        <Tooltip title={t('logs.tooltip.autoscroll')}>
          <span>{t('logs.autoscroll')} <Switch checked={autoScroll} onChange={setAutoScroll} style={{ marginLeft: 6 }} /></span>
        </Tooltip>
        <Tooltip title={t('logs.tooltip.filter_tqdm')}>
          <span>{t('logs.filter_tqdm')} <Switch checked={filterTqdm} onChange={setFilterTqdm} style={{ marginLeft: 6 }} /></span>
        </Tooltip>
        <Input
          placeholder={t('logs.search_placeholder')}
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          style={{ width: 160 }}
          size="small"
          allowClear
        />
        <Button size="small" onClick={clearLogs}>{t('logs.clear')}</Button>
        <Button size="small" onClick={copyAll}>{t('logs.copy')}</Button>
      </Space>
      <div 
        ref={containerRef} 
        style={{ 
          height: 320, 
          overflow: 'auto', 
          background: '#0b1020', 
          color: '#e6e9ef', 
          padding: 12, 
          borderRadius: 8, 
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', 
          fontSize: 12,
        }}
      >
        {displayLines.map((line, index) => renderLine(line, index))}
      </div>
    </div>
  )
}
