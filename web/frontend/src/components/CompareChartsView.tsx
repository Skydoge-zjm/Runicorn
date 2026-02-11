/**
 * CompareChartsView - Right panel showing metric comparison charts
 * 
 * Displays charts for metrics that are common to at least 2 selected runs.
 * Charts are displayed without legends since the left panel shows color mapping.
 * 
 * Optimization: Uses ECharts legend.selected to toggle series visibility
 * instead of re-rendering the entire chart when hiding/showing runs.
 */
import React, { useMemo, useState, useEffect } from 'react'
import { Row, Col, Empty, Spin, Card, Checkbox, Space, Button, Tooltip, theme } from 'antd'
import { LineChartOutlined, EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import MetricChart, { MetricsData } from './MetricChart'

interface CompareChartsViewProps {
  runIds: string[]
  visibleRunIds: Set<string>  // Which runs are visible in charts
  metricsMap: Map<string, MetricsData>
  runLabels: Map<string, string>  // runId -> display label (path or alias)
  colors: string[]
  loading: boolean
}

// X-axis keys to exclude from comparison
const X_AXIS_KEYS = new Set(['step', 'iter', 'batch', 'global_step', 'time', 'epoch', 'index'])

const CompareChartsView: React.FC<CompareChartsViewProps> = ({
  runIds,
  visibleRunIds,
  metricsMap,
  runLabels,
  colors,
  loading,
}) => {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  
  // Visible metrics state (all visible by default)
  const [visibleMetrics, setVisibleMetrics] = useState<Set<string>>(new Set())

  // Calculate common metrics (present in at least 2 runs)
  const commonMetrics = useMemo(() => {
    const metricCounts = new Map<string, number>()

    for (const [_, data] of metricsMap) {
      if (!data?.columns) continue
      const cols = new Set(data.columns)
      for (const col of cols) {
        if (!X_AXIS_KEYS.has(col)) {
          metricCounts.set(col, (metricCounts.get(col) || 0) + 1)
        }
      }
    }

    return Array.from(metricCounts.entries())
      .filter(([_, count]) => count >= 2)
      .map(([metric]) => metric)
      .sort()
  }, [metricsMap])

  // Initialize visible metrics when commonMetrics changes
  useEffect(() => {
    setVisibleMetrics(new Set(commonMetrics))
  }, [commonMetrics])

  // Determine best x-axis key available across runs
  const xAxisKey = useMemo(() => {
    const candidates = ['step', 'global_step', 'iter', 'batch', 'epoch', 'time']
    for (const candidate of candidates) {
      let found = false
      for (const [_, data] of metricsMap) {
        if (data?.columns?.includes(candidate)) {
          found = true
          break
        }
      }
      if (found) return candidate
    }
    return 'step'
  }, [metricsMap])

  // Toggle single metric visibility
  const toggleMetric = (metric: string) => {
    setVisibleMetrics(prev => {
      const next = new Set(prev)
      if (next.has(metric)) {
        next.delete(metric)
      } else {
        next.add(metric)
      }
      return next
    })
  }

  // Toggle all metrics
  const toggleAll = () => {
    if (visibleMetrics.size === commonMetrics.length) {
      setVisibleMetrics(new Set())
    } else {
      setVisibleMetrics(new Set(commonMetrics))
    }
  }

  // Metrics to display
  const displayedMetrics = commonMetrics.filter(m => visibleMetrics.has(m))
  
  // Count visible runs for empty state check
  const visibleRunCount = runIds.filter(id => visibleRunIds.has(id)).length

  // Build legend selected state for each run
  // Use runId as key to ensure uniqueness (labels may collide for same experiment)
  const legendSelected = useMemo(() => {
    const selected: Record<string, boolean> = {}
    for (const runId of runIds) {
      // Use runId as the series name key for uniqueness
      selected[runId] = visibleRunIds.has(runId)
    }
    return selected
  }, [runIds, visibleRunIds])

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: 300,
        }}
      >
        <Spin size="large" tip={t('experiments.loading_metrics') || 'Loading metrics...'} />
      </div>
    )
  }

  if (commonMetrics.length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: 300,
        }}
      >
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('experiments.no_common_metrics') || 'No common metrics found in selected runs'}
        />
      </div>
    )
  }

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: '0 4px' }}>
      {/* Header with metric toggles */}
      <Card
        size="small"
        style={{ marginBottom: 12, borderRadius: 8 }}
        styles={{ body: { padding: '8px 16px' } }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <LineChartOutlined style={{ color: token.colorPrimary }} />
            <span style={{ fontWeight: 500 }}>
              {t('experiments.common_metrics') || 'Common Metrics'}
            </span>
          </div>
          
          {/* Toggle all button */}
          <Tooltip title={visibleMetrics.size === commonMetrics.length 
            ? (t('experiments.hide_all') || 'Hide All') 
            : (t('experiments.show_all') || 'Show All')}>
            <Button
              size="small"
              type="text"
              icon={visibleMetrics.size === commonMetrics.length ? <EyeOutlined /> : <EyeInvisibleOutlined />}
              onClick={toggleAll}
            />
          </Tooltip>
          
          {/* Metric checkboxes */}
          <Space size={[8, 4]} wrap style={{ flex: 1 }}>
            {commonMetrics.map(metric => (
              <Checkbox
                key={metric}
                checked={visibleMetrics.has(metric)}
                onChange={() => toggleMetric(metric)}
                style={{ fontSize: 12 }}
              >
                {metric}
              </Checkbox>
            ))}
          </Space>
          
          <span style={{ color: token.colorTextSecondary, fontSize: 12, flexShrink: 0 }}>
            {displayedMetrics.length}/{commonMetrics.length}
          </span>
        </div>
      </Card>

      {/* Charts grid */}
      {displayedMetrics.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('experiments.no_metrics_selected') || 'No metrics selected'}
          style={{ marginTop: 48 }}
        />
      ) : visibleRunCount < 2 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('experiments.need_two_visible') || 'Need at least 2 visible runs to compare'}
          style={{ marginTop: 48 }}
        />
      ) : (
        <Row gutter={[12, 12]}>
          {displayedMetrics.map((metric, index) => {
            // Include ALL runs that have this metric (not just visible ones)
            // Visibility is controlled via legendSelected
            const runsWithMetric = runIds.filter(
              id => metricsMap.has(id) && metricsMap.get(id)?.columns?.includes(metric)
            )
            // Build colors array matching the runs order
            // Color is determined by the run's position in the original runIds array
            const chartColors = runsWithMetric.map(id => colors[runIds.indexOf(id)] || token.colorTextDisabled)
            
            return (
              <Col xs={24} lg={12} key={metric}>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <Card
                    size="small"
                    style={{ borderRadius: 8 }}
                    styles={{ body: { padding: 8 } }}
                  >
                    <MetricChart
                      runs={runsWithMetric.map(id => ({
                        id,
                        label: runLabels.get(id) || id.slice(-12),
                        metrics: metricsMap.get(id)!,
                      }))}
                      xKey={xAxisKey}
                      yKey={metric}
                      title={metric}
                      height={280}
                      group="inline-compare"
                      showLegend={false}
                      colors={chartColors}
                      legendSelected={legendSelected}
                    />
                  </Card>
                </motion.div>
              </Col>
            )
          })}
        </Row>
      )}
    </div>
  )
}

export default CompareChartsView
