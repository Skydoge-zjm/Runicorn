import React from 'react'
import { Card, Skeleton, Row, Col, Space } from 'antd'
import designTokens from '../styles/designTokens'

/**
 * Loading Skeleton for Experiment List Page
 */
export function ExperimentListSkeleton() {
  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* Statistics Cards Skeleton */}
      <Row gutter={[designTokens.spacing.md, designTokens.spacing.md]}>
        {[1, 2, 3, 4].map(i => (
          <Col xs={24} sm={12} md={6} key={i}>
            <Card>
              <Skeleton active paragraph={{ rows: 1 }} />
            </Card>
          </Col>
        ))}
      </Row>
      
      {/* Table Skeleton */}
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* Table Header */}
          <Skeleton.Button active style={{ width: '100%', height: 40 }} />
          {/* Table Rows */}
          {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
            <Skeleton key={i} active paragraph={{ rows: 0 }} />
          ))}
        </Space>
      </Card>
    </Space>
  )
}

/**
 * Loading Skeleton for Run Detail Page
 */
export function RunDetailSkeleton() {
  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* Run Info Card */}
      <Card>
        <Skeleton active paragraph={{ rows: 4 }} />
      </Card>
      
      {/* GPU Card */}
      <Card>
        <Skeleton active paragraph={{ rows: 2 }} />
      </Card>
      
      {/* Metrics Charts */}
      <Row gutter={[designTokens.spacing.md, designTokens.spacing.md]}>
        {[1, 2, 3, 4].map(i => (
          <Col xs={24} md={12} key={i}>
            <Card>
              <Skeleton.Image 
                active 
                style={{ width: '100%', height: 300 }} 
              />
            </Card>
          </Col>
        ))}
      </Row>
      
      {/* Logs Card */}
      <Card>
        <Skeleton active paragraph={{ rows: 6 }} />
      </Card>
    </Space>
  )
}

/**
 * Loading Skeleton for Metric Charts
 */
export function MetricChartSkeleton({ height = 320 }: { height?: number }) {
  return (
    <Card 
      size="small"
      style={{ 
        marginBottom: designTokens.spacing.md,
        borderRadius: designTokens.borderRadius.md,
      }}
    >
      {/* Controls Skeleton */}
      <Skeleton.Button active size="small" style={{ width: '100%', marginBottom: 12 }} />
      
      {/* Chart Skeleton */}
      <Skeleton.Image 
        active 
        style={{ width: '100%', height }} 
      />
    </Card>
  )
}

/**
 * Generic Loading Skeleton
 */
export function GenericLoadingSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <Card>
      <Skeleton active paragraph={{ rows }} />
    </Card>
  )
}

export default {
  ExperimentList: ExperimentListSkeleton,
  RunDetail: RunDetailSkeleton,
  MetricChart: MetricChartSkeleton,
  Generic: GenericLoadingSkeleton,
}
