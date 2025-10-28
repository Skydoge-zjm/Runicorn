/**
 * FancyMetricCard - Enhanced Chart Card with Gradient Border
 * 
 * Wraps metric charts with fancy styling
 */

import React from 'react'
import { Card, Space, Button, Tooltip } from 'antd'
import { 
  FullscreenOutlined, 
  DownloadOutlined, 
  LineChartOutlined 
} from '@ant-design/icons'
import { motion } from 'framer-motion'
import { runDetailPageConfig } from '../../config/animation_config/run_detail'
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
  const config = runDetailPageConfig.metricCard
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={config.hoverEffect}
      transition={{ duration: 0.3 }}
    >
      <Card
        title={
          <Space>
            <LineChartOutlined style={{ color: config.headerIconColor }} />
            <span style={{ 
              fontWeight: config.headerFontWeight, 
              fontSize: config.headerFontSize 
            }}>
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
          borderRadius: config.borderRadius,
          overflow: 'hidden',
          boxShadow: config.boxShadow,
          position: 'relative'
        }}
        headStyle={{
          padding: config.headerPadding,
          background: `linear-gradient(135deg, ${config.headerGradient[0]}15, ${config.headerGradient[1]}15)`,
          borderBottom: `2px solid ${config.headerGradient[0]}30`
        }}
        bodyStyle={{ padding: 16 }}
      >
        {children}
      </Card>
    </motion.div>
  )
}

export default FancyMetricCard

