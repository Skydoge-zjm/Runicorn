/**
 * ServerStatusLight - Pulsing Status Indicator
 * 
 * Shows online/offline/connecting status with pulse animation
 */

import React from 'react'
import { motion } from 'framer-motion'
import { remotePageConfig } from '../../config/animation_config/remote'

interface ServerStatusLightProps {
  status: 'online' | 'offline' | 'connecting'
  label?: string
}

export const ServerStatusLight: React.FC<ServerStatusLightProps> = ({
  status,
  label
}) => {
  const config = remotePageConfig.statusLight
  const color = config.colors[status]
  const shouldPulse = status === 'online' || status === 'connecting'
  
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <motion.div
        style={{
          width: config.size,
          height: config.size,
          borderRadius: '50%',
          background: color,
          position: 'relative'
        }}
        animate={shouldPulse ? {
          boxShadow: config.pulseAnimation.boxShadow
        } : {}}
        transition={{
          ...config.pulseAnimation.transition,
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

