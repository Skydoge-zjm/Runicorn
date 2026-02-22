/**
 * StatusTag - Simple status indicator using antd Tag
 *
 * Replaces AnimatedStatusBadge with a clean, static design.
 */

import React from 'react'
import { Tag } from 'antd'
import {
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'

interface StatusTagProps {
  status: string
}

const StatusTag: React.FC<StatusTagProps> = ({ status }) => {
  const s = status.toLowerCase()
  const label = status.charAt(0).toUpperCase() + status.slice(1)

  switch (s) {
    case 'running':
      return <Tag icon={<SyncOutlined spin />} color="processing">{label}</Tag>
    case 'finished':
      return <Tag icon={<CheckCircleOutlined />} color="success">{label}</Tag>
    case 'failed':
      return <Tag icon={<CloseCircleOutlined />} color="error">{label}</Tag>
    case 'interrupted':
      return <Tag icon={<ClockCircleOutlined />} color="warning">{label}</Tag>
    default:
      return <Tag>{label}</Tag>
  }
}

export default StatusTag
