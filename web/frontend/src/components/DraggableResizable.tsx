import React, { useEffect, useRef, useState } from 'react'

export interface DraggableResizableProps {
  id: string
  defaultPos: { left: number; top: number; width: number; height: number }
  min?: { width?: number; height?: number }
  children: React.ReactNode
}

type Rect = { left: number; top: number; width: number; height: number }

export default function DraggableResizable({ id, defaultPos, min, children }: DraggableResizableProps) {
  const key = `dr_${id}`
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [pos, setPos] = useState<Rect>(() => {
    try {
      const raw = localStorage.getItem(key)
      if (raw) return JSON.parse(raw)
    } catch {}
    return defaultPos
  })
  const draggingRef = useRef<{ startX: number; startY: number; startLeft: number; startTop: number } | null>(null)
  const resizingRef = useRef<{ startW: number; startH: number; startX: number; startY: number } | null>(null)

  useEffect(() => {
    try { localStorage.setItem(key, JSON.stringify(pos)) } catch {}
  }, [pos.left, pos.top, pos.width, pos.height])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const rect = wrapperRef.current?.getBoundingClientRect()
      if (draggingRef.current && rect) {
        const { startX, startY, startLeft, startTop } = draggingRef.current
        const dx = e.clientX - startX
        const dy = e.clientY - startY
        setPos((p: Rect) => {
          let left = startLeft + dx
          let top = startTop + dy
          // clamp: left within container width, top no bottom clamp so container can grow
          left = Math.max(0, Math.min(left, Math.max(0, rect.width - p.width)))
          top = Math.max(0, top)
          return { ...p, left, top }
        })
      } else if (resizingRef.current && rect) {
        const { startW, startH, startX, startY } = resizingRef.current
        let nw = startW + (e.clientX - startX)
        let nh = startH + (e.clientY - startY)
        const minW = min?.width ?? 240
        const minH = min?.height ?? 160
        setPos((p: Rect) => {
          // width cannot exceed container's remaining width; height can grow (wrapper will expand)
          const maxW = Math.max(minW, rect.width - p.left)
          const width = Math.min(Math.max(minW, nw), maxW)
          const height = Math.max(minH, nh)
          return { ...p, width, height }
        })
      }
    }
    const onUp = () => {
      draggingRef.current = null
      resizingRef.current = null
      // ensure echarts reacts after finishing drag/resize
      try { window.dispatchEvent(new Event('resize')) } catch {}
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [min?.width, min?.height])

  // Trigger resize on size changes so echarts-for-react resizes
  useEffect(() => {
    try { window.dispatchEvent(new Event('resize')) } catch {}
  }, [pos.width, pos.height])

  return (
    <div ref={wrapperRef} style={{ position: 'relative', width: '100%', height: Math.max(pos.top + pos.height + 12, 280) }}>
      <div
        style={{ position: 'absolute', left: pos.left, top: pos.top, width: pos.width, height: pos.height, boxSizing: 'border-box' }}
      >
        {/* Move handle: small button at top-left, won't block chart interactions */}
        <div
          style={{ position: 'absolute', left: 6, top: 6, width: 16, height: 16, cursor: 'move', zIndex: 3, borderRadius: 3, background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.5)' }}
          onMouseDown={(e) => {
            draggingRef.current = { startX: e.clientX, startY: e.clientY, startLeft: pos.left, startTop: pos.top }
            e.preventDefault()
            document.body.style.userSelect = 'none'
            document.body.style.cursor = 'grabbing'
          }}
          title="拖动移动图表"
        />
        <div style={{ width: '100%', height: '100%' }}>
          {children}
        </div>
        <div
          style={{ position: 'absolute', right: 2, bottom: 2, width: 16, height: 16, cursor: 'nwse-resize', zIndex: 3, background: 'transparent' }}
          onMouseDown={(e) => {
            resizingRef.current = { startW: pos.width, startH: pos.height, startX: e.clientX, startY: e.clientY }
            e.preventDefault(); e.stopPropagation()
            document.body.style.userSelect = 'none'
            document.body.style.cursor = 'nwse-resize'
          }}
          title="拖动右下角调整大小"
        />
      </div>
    </div>
  )
}
