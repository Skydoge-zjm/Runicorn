/**
 * CircularProgress - Circular Progress Indicator with Gradient
 * 
 * Used for GPU utilization, memory usage, etc.
 */

import React, { useEffect } from 'react'
import { motion, useSpring, useTransform } from 'framer-motion'

const GPU_PROGRESS_CONFIG = {
  size: 120,
  strokeWidth: 8,
  colors: {
    low: ['#52c41a', '#73d13d'] as [string, string],
    medium: ['#faad14', '#ffc53d'] as [string, string],
    high: ['#ff4d4f', '#ff7875'] as [string, string],
  },
} as const

interface CircularProgressProps {
  value: number  // 0-100
  label: string
  sublabel?: string
  size?: number
}

export const CircularProgress: React.FC<CircularProgressProps> = ({
  value,
  label,
  sublabel,
  size
}) => {
  const config = GPU_PROGRESS_CONFIG
  const radius = (size || config.size) / 2
  const strokeWidth = config.strokeWidth
  const normalizedRadius = radius - strokeWidth / 2
  const circumference = normalizedRadius * 2 * Math.PI
  
  // Determine color based on value
  const getGradientColors = (val: number): [string, string] => {
    if (val < 50) return config.colors.low
    if (val < 80) return config.colors.medium
    return config.colors.high
  }
  
  const gradientColors = getGradientColors(value)
  const gradientId = `gradient-${label.replace(/\s/g, '-')}`
  
  // Animated progress value
  const spring = useSpring(0, {
    damping: 30,
    stiffness: 100
  })
  
  const animatedValue = useTransform(spring, (v) => Math.round(v))
  const strokeDashoffset = useTransform(
    spring,
    (v) => circumference - (v / 100) * circumference
  )
  
  useEffect(() => {
    spring.set(value)
  }, [value, spring])
  
  return (
    <div style={{ 
      position: 'relative', 
      width: size || config.size, 
      height: size || config.size,
      display: 'inline-block'
    }}>
      <svg
        height={size || config.size}
        width={size || config.size}
        style={{ transform: 'rotate(-90deg)' }}
      >
        {/* Gradient definition */}
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={gradientColors[0]} />
            <stop offset="100%" stopColor={gradientColors[1]} />
          </linearGradient>
        </defs>
        
        {/* Background circle */}
        <circle
          stroke="#f0f0f0"
          fill="transparent"
          strokeWidth={strokeWidth}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        
        {/* Progress circle */}
        <motion.circle
          stroke={`url(#${gradientId})`}
          fill="transparent"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          style={{
            strokeDashoffset,
            strokeLinecap: 'round'
          }}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
      </svg>
      
      {/* Center label */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        textAlign: 'center'
      }}>
        <motion.div style={{
          fontSize: 28,
          fontWeight: 700,
          lineHeight: 1,
          fontVariantNumeric: 'tabular-nums'
        }}>
          <motion.span>{animatedValue}</motion.span>%
        </motion.div>
        {sublabel && (
          <div style={{
            fontSize: 12,
            color: '#8c8c8c',
            marginTop: 4
          }}>
            {sublabel}
          </div>
        )}
      </div>
    </div>
  )
}

export default CircularProgress

