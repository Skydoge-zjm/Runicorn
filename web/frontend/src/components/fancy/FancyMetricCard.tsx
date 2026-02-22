/**
 * FancyMetricCard - Chart Card wrapper
 *
 * Wraps metric charts with clean Card styling.
 */

import React from 'react'
import { Card, Space, Button, Tooltip } from 'antd'
import {
  FullscreenOutlined,
  DownloadOutlined,
  LineChartOutlined
} from '@ant-design/icons'
import type { ReactNode } from 'react'

interface FancyMetricCardProps {
  title: string
  children: ReactNode
  onFullscreen?: () => void
  onDownload?: () => void
  extra?: ReactNode
}

export const FancyMetricCard: React.FC<FancyMetricCardProps> = ({
  title,
  children,
  onFullscreen,
  onDownload,
  extra
}) => {
  return (
    <div style={{ transition: 'box-shadow 0.15s ease' }}>
      <Card
        title={
          <Space>
            <LineChartOutlined />
            <span style={{ fontWeight: 600, fontSize: 14 }}>
              {title}
            </span>
          </Space>
        }
        extra={
          extra || (
            <Space>
              {onDownload && (
                <Tooltip title="Download Chart">
                  <Button
                    type="text"
                    icon={<DownloadOutlined />}
                    size="small"
                    onClick={onDownload}
                  />
                </Tooltip>
              )}
              {onFullscreen && (
                <Tooltip title="Fullscreen">
                  <Button
                    type="text"
                    icon={<FullscreenOutlined />}
                    size="small"
                    onClick={onFullscreen}
                  />
                </Tooltip>
              )}
            </Space>
          )
        }
        bordered={false}
        style={{
          borderRadius: 8,
          overflow: 'hidden',
        }}
        bodyStyle={{ padding: 16 }}
      >
        {children}
      </Card>
    </div>
  )
}

export default FancyMetricCard

