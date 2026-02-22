/**
 * ServerStatusLight - Pulsing Status Indicator
 * 
 * Shows online/offline/connecting status with pulse animation
 */

import React from 'react'
import { motion } from 'framer-motion'

const STATUS_COLORS: Record<string, string> = {
  online: '#52c41a',
  offline: '#ff4d4f',
  connecting: '#faad14',
}

interface ServerStatusLightProps {
  status: 'online' | 'offline' | 'connecting'
  label?: string
}

export const ServerStatusLight: React.FC<ServerStatusLightProps> = ({
  status,
  label
}) => {
  const color = STATUS_COLORS[status] || STATUS_COLORS.offline
  const shouldPulse = status === 'online' || status === 'connecting'
  
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <motion.div
        style={{
          width: 12,
          height: 12,
          borderRadius: '50%',
          background: color,
          position: 'relative'
        }}
        animate={shouldPulse ? {
          boxShadow: [
            '0 0 0 0 rgba(82, 196, 26, 0.7)',
            '0 0 0 10px rgba(82, 196, 26, 0)',
          ]
        } : {}}
        transition={{
          duration: 1.5,
          ease: 'easeOut' as const,
          repeat: shouldPulse ? Infinity : 0
        }}
      />
      {label && (
        <span style={{ fontSize: 13, color: '#595959' }}>
          {label}
        </span>
      )}
    </div>
  )
}

export default ServerStatusLight

