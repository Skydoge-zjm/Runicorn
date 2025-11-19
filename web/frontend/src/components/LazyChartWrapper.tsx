import React, { useEffect, useRef, useState } from 'react'
import { Skeleton } from 'antd'

interface LazyChartWrapperProps {
  children: React.ReactNode
  height?: number | string
  threshold?: number
  placeholder?: React.ReactNode
}

export default function LazyChartWrapper({ 
  children, 
  height = 320, 
  threshold = 0.1,
  placeholder 
}: LazyChartWrapperProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [hasLoaded, setHasLoaded] = useState(false)

  useEffect(() => {
    if (hasLoaded) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setHasLoaded(true)
          observer.disconnect()
        }
      },
      {
        rootMargin: '200px', // Pre-load before element enters viewport
        threshold
      }
    )

    if (ref.current) {
      observer.observe(ref.current)
    }

    return () => observer.disconnect()
  }, [hasLoaded, threshold])

  return (
    <div ref={ref} style={{ minHeight: height, width: '100%' }}>
      {hasLoaded ? (
        children
      ) : (
        placeholder || (
          <div style={{ 
            height, 
            width: '100%',
            padding: 16,
            background: 'rgba(0,0,0,0.02)', 
            borderRadius: 8,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center'
          }}>
            <Skeleton active paragraph={{ rows: 4 }} title={false} />
          </div>
        )
      )}
    </div>
  )
}
