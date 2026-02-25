import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { Button, Input, Space, Switch, Tag, Tooltip, message, theme } from 'antd'
import { DownOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import AnsiToHtml from 'ansi-to-html'
import { useVirtualizer } from '@tanstack/react-virtual'

// Constants
const MAX_LINES = 5000
const RECONNECT_BASE_MS = 500
const RECONNECT_MAX_MS = 10000
const SCROLL_BOTTOM_THRESHOLD = 50

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

// Dark theme ANSI converter
const darkConverter = new AnsiToHtml({
  fg: '#e6e9ef',
  bg: '#000000',
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

// Light theme ANSI converter
const lightConverter = new AnsiToHtml({
  fg: '#374151',
  bg: '#ffffff',
  newline: false,
  escapeXML: true,
  colors: {
    0: '#374151',   // black
    1: '#DC2626',   // red
    2: '#16A34A',   // green
    3: '#CA8A04',   // yellow
    4: '#2563EB',   // blue
    5: '#9333EA',   // magenta
    6: '#0891B2',   // cyan
    7: '#6B7280',   // white
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
  const { token } = theme.useToken()
  const isDark = parseInt((token.colorBgBase || '#ffffff').replace('#', '').slice(0, 2), 16) < 128
  const ansiConverter = isDark ? darkConverter : lightConverter
  
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
      
      // Batch incoming messages via rAF to reduce GC pressure from high-frequency updates
      const pendingLines: string[] = []
      let rafId: number | null = null
      const flushPending = () => {
        rafId = null
        if (pendingLines.length === 0) return
        const batch = pendingLines.splice(0)
        setAllLines((prev) => {
          const next = prev.concat(batch)
          return next.length > MAX_LINES ? next.slice(-MAX_LINES) : next
        })
      }
      ws.onmessage = (ev) => {
        if (!mountedRef.current) return
        pendingLines.push(String(ev.data))
        if (rafId === null) {
          rafId = requestAnimationFrame(flushPending)
        }
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

  // Cache ANSI HTML conversions to avoid re-parsing on scroll
  const htmlLines = useMemo(() => {
    return displayLines.map(line => {
      try {
        return ansiConverter.toHtml(line)
      } catch {
        return escapeHtml(line)
      }
    })
  }, [displayLines, ansiConverter])

  // Virtual scroll
  const virtualizer = useVirtualizer({
    count: displayLines.length,
    getScrollElement: () => containerRef.current,
    estimateSize: () => 20,
    overscan: 30,
  })

  // Smart auto-scroll: disable when user scrolls away from bottom
  const handleScroll = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < SCROLL_BOTTOM_THRESHOLD
    if (!atBottom && autoScroll) {
      setAutoScroll(false)
    }
  }, [autoScroll])

  // Auto-scroll when new lines arrive
  useEffect(() => {
    if (autoScroll && displayLines.length > 0) {
      virtualizer.scrollToIndex(displayLines.length - 1, { align: 'end' })
    }
  }, [displayLines.length, autoScroll, virtualizer])

  // Resume auto-scroll and jump to bottom
  const resumeAutoScroll = useCallback(() => {
    setAutoScroll(true)
    if (displayLines.length > 0) {
      virtualizer.scrollToIndex(displayLines.length - 1, { align: 'end' })
    }
  }, [virtualizer, displayLines.length])

  // Highlight search keyword in pre-converted HTML
  const highlightHtml = useCallback((html: string) => {
    if (!searchKeyword) return html
    const regex = new RegExp(`(${escapeRegex(searchKeyword)})`, 'gi')
    return html.replace(regex, '<mark style="background:#f0c674;color:#1d1f21">$1</mark>')
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
    <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      <Space style={{ marginBottom: 8, flexShrink: 0, padding: '8px 12px 0' }} wrap>
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
        onScroll={handleScroll}
        style={{
          flex: 1,
          minHeight: 200,
          overflow: 'auto',
          background: isDark ? '#000000' : '#ffffff',
          color: isDark ? '#e6e9ef' : '#374151',
          padding: '12px 0',
          borderRadius: 8,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
          fontSize: 12,
        }}
      >
        <div style={{ height: virtualizer.getTotalSize(), width: '100%', position: 'relative' }}>
          {virtualizer.getVirtualItems().map(virtualRow => (
            <div
              key={virtualRow.key}
              data-index={virtualRow.index}
              ref={virtualizer.measureElement}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualRow.start}px)`,
                display: 'flex',
                padding: '0 12px',
                minHeight: 20,
              }}
            >
              <span style={{
                color: isDark ? '#6c7a89' : '#9CA3AF',
                minWidth: 50,
                textAlign: 'right',
                paddingRight: 12,
                userSelect: 'none',
                flexShrink: 0,
              }}>
                {virtualRow.index + 1}
              </span>
              <span
                style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}
                dangerouslySetInnerHTML={{ __html: highlightHtml(htmlLines[virtualRow.index]) }}
              />
            </div>
          ))}
        </div>
      </div>
      {!autoScroll && displayLines.length > 0 && (
        <Button
          size="small"
          icon={<DownOutlined />}
          onClick={resumeAutoScroll}
          style={{
            position: 'absolute',
            bottom: 16,
            right: 24,
            zIndex: 10,
            opacity: 0.9,
          }}
        >
          {t('logs.resume_autoscroll')}
        </Button>
      )}
    </div>
  )
}
