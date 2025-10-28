/**
 * AnimatedStatusBadge - Animated Status Badge with Pulse Effect
 * 
 * Features:
 * - Gradient backgrounds per status
 * - Pulse animation for running state
 * - Spring entrance animation
 * - Rotating icon for running
 */

import React from 'react'
import { Tag } from 'antd'
import { motion } from 'framer-motion'
import {
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'
import { componentAnimationConfig } from '../../config/animation_config'

interface AnimatedStatusBadgeProps {
  status: 'running' | 'finished' | 'failed' | 'interrupted' | string
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  running: <SyncOutlined spin />,
  finished: <CheckCircleOutlined />,
  failed: <CloseCircleOutlined />,
  interrupted: <ClockCircleOutlined />
}

export const AnimatedStatusBadge: React.FC<AnimatedStatusBadgeProps> = ({ status }) => {
  const statusKey = status.toLowerCase()
  const config = componentAnimationConfig.statusBadge
  const statusConfig = config.statuses[statusKey as keyof typeof config.statuses] || config.statuses.interrupted
  const icon = STATUS_ICONS[statusKey] || STATUS_ICONS.interrupted
  
  return (
    <motion.div
      initial={config.entrance.initial}
      animate={config.entrance.animate}
      transition={config.entrance.transition}
      style={{ display: 'inline-block' }}
    >
      <motion.div
        animate={statusConfig.pulse ? {
          boxShadow: config.pulse.boxShadow
        } : {}}
        transition={{
          ...config.pulse.transition,
          repeat: statusConfig.pulse ? Infinity : 0
        }}
        style={{
          display: 'inline-block',
          borderRadius: config.style.borderRadius
        }}
      >
        <Tag
          icon={icon}
          style={{
            fontSize: config.style.fontSize,
            padding: config.style.padding,
            borderRadius: config.style.borderRadius,
            fontWeight: config.style.fontWeight,
            background: `linear-gradient(135deg, ${statusConfig.gradientColors[0]}, ${statusConfig.gradientColors[1]})`,
            border: 'none',
            color: '#fff',
            margin: 0
          }}
        >
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </Tag>
      </motion.div>
    </motion.div>
  )
}

export default AnimatedStatusBadge

