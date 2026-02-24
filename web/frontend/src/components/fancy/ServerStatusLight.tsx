/**
 * ServerStatusLight - Pulsing Status Indicator
 * 
 * Shows online/offline/connecting status with pulse animation
 */

import { motion } from 'framer-motion'
import { theme } from 'antd'

interface ServerStatusLightProps {
  status: 'online' | 'offline' | 'connecting'
  label?: string
}

export const ServerStatusLight: React.FC<ServerStatusLightProps> = ({
  status,
  label
}) => {
  const { token } = theme.useToken()

  const statusColors: Record<string, string> = {
    online: token.colorSuccess,
    offline: token.colorError,
    connecting: token.colorWarning,
  }

  const color = statusColors[status] || statusColors.offline
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
            `0 0 0 0 ${color}b3`,
            `0 0 0 10px ${color}00`,
          ]
        } : {}}
        transition={{
          duration: 1.5,
          ease: 'easeOut' as const,
          repeat: shouldPulse ? Infinity : 0
        }}
      />
      {label && (
        <span style={{ fontSize: 13, color: token.colorTextSecondary }}>
          {label}
        </span>
      )}
    </div>
  )
}

export default ServerStatusLight

