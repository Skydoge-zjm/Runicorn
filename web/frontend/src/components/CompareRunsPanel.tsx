/**
 * CompareRunsPanel - Left panel showing selected runs info in compare mode
 * 
 * Displays each run with a color dot matching the chart line color,
 * along with basic run information (path, alias, status).
 * 
 * Features:
 * - Click run card to navigate to detail page
 * - Eye icon to toggle run visibility in charts
 * - Auto-refresh indicator when running experiments exist
 */
import { useMemo } from 'react'
import { Button, Tag, Tooltip, theme } from 'antd'
import { ArrowLeftOutlined, CheckCircleOutlined, CloseCircleOutlined, SyncOutlined, QuestionCircleOutlined, EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'

export interface CompareRunInfo {
  runId: string
  path: string
  alias: string | null
  status: string
}

interface CompareRunsPanelProps {
  runs: CompareRunInfo[]
  colors: string[]
  visibleRunIds: Set<string>
  onToggleRunVisibility: (runId: string) => void
  onHoverRun?: (runId: string | null) => void
  hoveredRunId?: string | null
  onAddRuns: () => void
  onBack: () => void
  style?: React.CSSProperties
}

const CompareRunsPanel: React.FC<CompareRunsPanelProps> = ({
  runs,
  colors,
  visibleRunIds,
  onToggleRunVisibility,
  onHoverRun,
  hoveredRunId,
  onAddRuns: _onAddRuns,
  onBack,
  style,
}) => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { token } = theme.useToken()
  
  // Status icon mapping using design tokens
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'finished':
        return <CheckCircleOutlined style={{ color: token.colorSuccess }} />
      case 'failed':
        return <CloseCircleOutlined style={{ color: token.colorError }} />
      case 'running':
        return <SyncOutlined spin style={{ color: token.colorPrimary }} />
      default:
        return <QuestionCircleOutlined style={{ color: token.colorTextDisabled }} />
    }
  }
  
  // Check if any run is still running
  const hasRunning = useMemo(() => runs.some(r => r.status === 'running'), [runs])
  
  // Count visible runs
  const visibleCount = runs.filter(r => visibleRunIds.has(r.runId)).length

  return (
    <div
      style={{
        ...style,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: 0,
        borderRight: `1px solid ${token.colorBorderSecondary}`,
        background: token.colorBgLayout,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px',
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          background: token.colorBgContainer,
          flexShrink: 0,
        }}
      >
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={onBack}
          style={{ marginBottom: 8, padding: '4px 8px' }}
        >
          {t('experiments.back_to_list')}
        </Button>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: token.colorText }}>
            {t('experiments.comparing_runs', { count: runs.length })}
          </div>
        </div>
        {/* Visible count */}
        <div style={{ fontSize: 11, color: token.colorTextSecondary, marginTop: 2 }}>
          {t('experiments.visible_runs', { count: visibleCount, total: runs.length })}
        </div>
        {/* Auto-refresh indicator */}
        {hasRunning && (
          <div style={{ 
            fontSize: 11, 
            color: token.colorPrimary, 
            marginTop: 4,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}>
            <SyncOutlined spin style={{ fontSize: 10 }} />
            {t('experiments.auto_refreshing')}
          </div>
        )}
      </div>

      {/* Runs list */}
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          padding: '8px',
          minHeight: 0,
        }}
      >
        {runs.map((run, index) => {
          const isVisible = visibleRunIds.has(run.runId)
          const isHovered = hoveredRunId === run.runId
          const runColor = colors[index] || token.colorTextDisabled
          return (
            <motion.div
              key={run.runId}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              style={{
                padding: '10px 12px',
                marginBottom: 8,
                background: token.colorBgContainer,
                borderRadius: 8,
                border: isHovered ? `2px solid ${runColor}` : `1px solid ${token.colorBorderSecondary}`,
                boxShadow: isHovered ? `0 0 8px ${runColor}40` : '0 1px 2px rgba(0,0,0,0.03)',
                opacity: isVisible ? 1 : 0.5,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onClick={() => navigate(`/runs/${run.runId}`)}
              onMouseEnter={() => onHoverRun?.(run.runId)}
              onMouseLeave={() => onHoverRun?.(null)}
              whileHover={{ scale: 1.01, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
            >
              {/* Color dot + Run ID + Eye toggle */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background: isVisible ? (colors[index] || token.colorTextDisabled) : token.colorTextDisabled,
                    flexShrink: 0,
                  }}
                />
                <Tooltip title={run.runId}>
                  <code
                    style={{
                      fontSize: 11,
                      color: token.colorTextSecondary,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      flex: 1,
                    }}
                  >
                    {run.runId.slice(-12)}
                  </code>
                </Tooltip>
                {getStatusIcon(run.status)}
                {/* Eye toggle */}
                <Tooltip title={isVisible 
                  ? (t('experiments.hide_run')) 
                  : (t('experiments.show_run'))}>
                  <span
                    onClick={(e) => {
                      e.stopPropagation()
                      onToggleRunVisibility(run.runId)
                    }}
                    style={{ 
                      cursor: 'pointer', 
                      color: isVisible ? token.colorPrimary : token.colorTextDisabled,
                      display: 'flex',
                      alignItems: 'center',
                    }}
                  >
                    {isVisible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                  </span>
                </Tooltip>
              </div>

              {/* Path */}
              <Tooltip title={`${t('experiments.click_to_view')}: ${run.path}`}>
                <div
                  style={{
                    fontSize: 12,
                    color: token.colorPrimary,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    marginBottom: run.alias ? 4 : 0,
                  }}
                >
                  {run.path}
                </div>
              </Tooltip>

              {/* Alias */}
              {run.alias && (
                <Tag color="purple" style={{ fontSize: 11, marginTop: 2 }}>
                  {run.alias}
                </Tag>
              )}
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

export default CompareRunsPanel
