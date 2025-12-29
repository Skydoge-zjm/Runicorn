import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Table, Button, Card, Space, Input, Select, Tag, Statistic, Row, Col, message, Modal, Tooltip, Empty, Dropdown, Badge, Checkbox, notification } from 'antd'
import { SearchOutlined, ReloadOutlined, DeleteOutlined, ExportOutlined, LineChartOutlined, EyeOutlined, DownOutlined, FileExcelOutlined, FileTextOutlined, FilterOutlined, SyncOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, FilePdfOutlined, HeartOutlined, UndoOutlined, ExperimentOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useSettings } from '../contexts/SettingsContext'
import { checkAllStatus, softDeleteRuns } from '../api'
import RecycleBin from '../components/RecycleBin'
import { ExperimentListSkeleton } from '../components/LoadingSkeleton'
import ResizableTitle from '../components/ResizableTitle'
import { useColumnWidths } from '../hooks/useColumnWidths'
import FancyStatCard from '../components/fancy/FancyStatCard'
import FancyEmpty from '../components/fancy/FancyEmpty'
import AnimatedStatusBadge from '../components/fancy/AnimatedStatusBadge'
import { useSuccessConfetti } from '../hooks/useSuccessConfetti'
import { StaggerContainer, StaggerItem } from '../components/animations/PageTransition'
import { experimentsPageConfig } from '../config/animation_config'
import logger from '../utils/logger'
import type { ColumnsType, TableProps } from 'antd/es/table'
import type { SorterResult } from 'antd/es/table/interface'
import '../styles/resizable-table.css'
import '../styles/enhanced-table.css'

// Define ResizeCallbackData type locally
interface ResizeCallbackData {
  size: { width: number }
}

interface RunData {
  run_id: string
  project: string
  name: string
  status: string
  created: string
  summary: any
  pid?: number
  best_metric_value?: number
  best_metric_name?: string
  assets_count?: number
}

interface FilterState {
  projects: string[]
  statuses: string[]
  dateRange: [string, string] | null
}

// Utility function for safe CSV value
const csvEscape = (value: any): string => {
  if (value === null || value === undefined) return ''
  const str = String(value)
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`
  }
  return str
}

const ExperimentPage: React.FC = () => {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { settings, setSettings } = useSettings()
  const [runs, setRuns] = useState<RunData[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([])
  const [searchText, setSearchText] = useState('')
  const [projectFilter, setProjectFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [projects, setProjects] = useState<string[]>([])
  const [stats, setStats] = useState({ total: 0, running: 0, finished: 0, failed: 0 })
  const [refreshInterval, setRefreshInterval] = useState<number | null>(null)
  
  // Use global settings for autoRefresh
  const autoRefresh = settings.autoRefresh
  const setAutoRefresh = (checked: boolean) => {
    setSettings({ ...settings, autoRefresh: checked })
  }
  // Column width management
  const defaultColumnWidths = {
    project: 120,
    name: 100,
    run_id: 280,          // 增加宽度以显示完整ID (20251009_082632_d5a4c7)
    status: 100,
    created: 210,         // 增加宽度以显示完整日期时间 (2025/10/09 08:26:32)
    best_metric: 200,
    assets: 120,
    actions: 120,
  }
  
  const { columnWidths, setColumnWidth } = useColumnWidths('experiments', defaultColumnWidths)
  
  const [sortedInfo, setSortedInfo] = useState<SorterResult<RunData>>({})
  const [pageSize, setPageSize] = useState(10)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [exportLoading, setExportLoading] = useState(false)
  const [statusCheckLoading, setStatusCheckLoading] = useState(false)
  
  // Handle column resize
  const handleResize = useCallback(
    (columnKey: string) =>
      (_: React.SyntheticEvent, { size }: ResizeCallbackData) => {
        setColumnWidth(columnKey, size.width)
      },
    [setColumnWidth]
  )
  
  const [recycleBinOpen, setRecycleBinOpen] = useState(false)
  
  // Success confetti effect
  const { trigger: triggerConfetti, ConfettiComponent } = useSuccessConfetti()

  // Persist user preferences
  useEffect(() => {
    const saved = localStorage.getItem('experiment_preferences')
    if (saved) {
      try {
        const prefs = JSON.parse(saved)
        if (prefs.pageSize) setPageSize(prefs.pageSize)
        // autoRefresh is now managed by global settings
      } catch {}
    }
  }, [])

  const savePreferences = useCallback(() => {
    localStorage.setItem('experiment_preferences', JSON.stringify({
      pageSize
      // autoRefresh is now managed by global settings
    }))
  }, [pageSize])

  useEffect(() => {
    savePreferences()
  }, [savePreferences])

  // Fetch runs from API with better error handling
  const fetchRuns = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true)
    try {
      const response = await fetch('/api/runs')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      // API returns array directly, not wrapped in object
      const runs = Array.isArray(data) ? data : (data.runs || [])
      
      // Map API response to our RunData interface
      const mappedRuns = runs.map((r: any) => {
        const created = r.created_time ? new Date(r.created_time * 1000) : new Date()
        
        return {
          run_id: r.id || r.run_id,
          project: r.project || 'default',
          name: r.name || 'unnamed',
          status: r.status || 'unknown',
          created: created.toISOString(),
          summary: r.summary || {},
          pid: r.pid,
          best_metric_value: r.best_metric_value,
          best_metric_name: r.best_metric_name,
          assets_count: r.assets_count || 0
        }
      })
      
      setRuns(mappedRuns)
      
      // Extract unique projects
      const uniqueProjects = [...new Set(mappedRuns.map((r: RunData) => r.project))] as string[]
      setProjects(uniqueProjects)
      
      // Calculate statistics
      const runStats = {
        total: mappedRuns.length,
        running: mappedRuns.filter((r: RunData) => r.status === 'running').length,
        finished: mappedRuns.filter((r: RunData) => r.status === 'finished').length,
        failed: mappedRuns.filter((r: RunData) => r.status === 'failed').length,
      }
      setStats(runStats)
      
      // Show notification for new runs if not initial load
      if (!showLoading && mappedRuns.length > runs.length) {
        notification.info({
          message: t('experiments.new_runs') || 'New runs detected',
          description: `${mappedRuns.length - runs.length} new run(s) added`,
          placement: 'bottomRight'
        })
      }
    } catch (error) {
      logger.error('Failed to fetch runs:', error)
      if (showLoading) {
        message.error(t('experiments.fetch_failed') || 'Failed to fetch runs')
      }
    }
    if (showLoading) setLoading(false)
  }, [runs.length, t])

  useEffect(() => {
    fetchRuns(true)
  }, [])

  // Auto-refresh functionality using global settings
  useEffect(() => {
    if (autoRefresh) {
      const interval = window.setInterval(() => {
        fetchRuns(false)  // Don't show loading for auto-refresh
      }, settings.refreshInterval * 1000)  // Use user-configured interval
      setRefreshInterval(interval)
    } else {
      if (refreshInterval) {
        window.clearInterval(refreshInterval)
        setRefreshInterval(null)
      }
    }
    return () => {
      if (refreshInterval) {
        window.clearInterval(refreshInterval)
      }
    }
  }, [autoRefresh, settings.refreshInterval])

  // Delete selected runs with better error handling
  const handleDelete = useCallback(() => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('experiments.select_one_delete') || 'Please select at least one run to delete')
      return
    }
    
    Modal.confirm({
      title: t('experiments.move_to_bin_title') || 'Move to Recycle Bin',
      content: (
        <div>
          <p>{t('experiments.soft_delete_confirm_content', { count: selectedRowKeys.length }) || `Move ${selectedRowKeys.length} selected runs to recycle bin?`}</p>
          <p style={{ color: '#1677ff', fontWeight: 500 }}>
            {t('experiments.soft_delete_note') || 'Files will be preserved and can be restored later.'}
          </p>
        </div>
      ),
      okText: t('experiments.move_to_bin') || 'Move to Bin',
      okType: 'primary',
      cancelText: t('experiments.cancel') || 'Cancel',
      okButtonProps: { loading: deleteLoading },
      onOk: async () => {
        setDeleteLoading(true)
        try {
          const result = await softDeleteRuns(selectedRowKeys)
          setSelectedRowKeys([])
          
          if (result.deleted_count > 0) {
            triggerConfetti()  // 🎉 Celebration effect!
            message.success(t('experiments.soft_delete_success', { count: result.deleted_count }) || `Moved ${result.deleted_count} runs to recycle bin`)
            await fetchRuns(false) // Refresh list without loading indicator
          } else {
            message.warning('No runs were moved to recycle bin')
          }
        } catch (error) {
          logger.error('Delete failed:', error)
          message.error(t('experiments.delete_failed') || 'Failed to move runs to recycle bin')
        } finally {
          setDeleteLoading(false)
        }
      },
    })
  }, [selectedRowKeys, t, deleteLoading, fetchRuns])

  // Export selected runs as JSON
  const handleExportJSON = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('experiments.select_one') || 'Please select at least one run to export')
      return
    }
    
    // For now, export as JSON with all run data
    const selectedRunData = runs.filter(r => selectedRowKeys.includes(r.run_id))
    
    try {
      // Create a comprehensive export object
      const exportData = {
        export_time: new Date().toISOString(),
        total_runs: selectedRunData.length,
        runs: selectedRunData.map(run => ({
          run_id: run.run_id,
          project: run.project,
          name: run.name,
          status: run.status,
          created: run.created,
          summary: run.summary,
        }))
      }
      
      // Convert to JSON string
      const jsonStr = JSON.stringify(exportData, null, 2)
      
      // Create blob and download
      const blob = new Blob([jsonStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `runicorn_export_${new Date().toISOString().slice(0, 10)}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      
      message.success(t('experiments.export_success', { count: selectedRunData.length }) || `Successfully exported ${selectedRunData.length} runs`)
    } catch (error) {
      logger.error('Export failed:', error)
      message.error(t('experiments.export_failed') || 'Failed to export runs')
    }
  }
  
  // Check status of all running experiments
  const handleStatusCheck = async () => {
    setStatusCheckLoading(true)
    try {
      const result = await checkAllStatus()
      if (result.updated > 0) {
        message.success(`Updated ${result.updated} experiment statuses`)
        fetchRuns(false) // Refresh list
      } else {
        message.info('All experiment statuses are up to date')
      }
    } catch (error) {
      logger.error('Status check failed:', error)
      message.error('Failed to check experiment statuses')
    } finally {
      setStatusCheckLoading(false)
    }
  }

  // Export selected runs as CSV with improved formatting
  const handleExportCSV = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('experiments.select_one') || 'Please select at least one run to export')
      return
    }
    
    setExportLoading(true)
    const selectedRunData = runs.filter(r => selectedRowKeys.includes(r.run_id))
    
    try {
      // Create comprehensive CSV with all important fields
      const headers = [
        'Run ID', 'Project', 'Experiment Name', 'Status', 'Created Time',
        'Final Loss', 'Learning Rate', 'Batch Size', 'Epochs',
        'Best Metric Value', 'Best Metric Name'
      ]
      
      // Create CSV rows with safe escaping
      const rows = selectedRunData.map(run => [
        csvEscape(run.run_id),
        csvEscape(run.project),
        csvEscape(run.name),
        csvEscape(run.status),
        csvEscape(new Date(run.created).toLocaleString()),
        csvEscape(run.summary?.final_loss?.toFixed(6) || ''),
        csvEscape(run.summary?.learning_rate || ''),
        csvEscape(run.summary?.batch_size || ''),
        csvEscape(run.summary?.total_epochs || ''),
        csvEscape(run.best_metric_value?.toFixed(4) || ''),
        csvEscape(run.best_metric_name || '')
      ])
      
      // Add UTF-8 BOM for Excel compatibility
      const BOM = '\uFEFF'
      const csvContent = BOM + [
        headers.join(','),
        ...rows.map(row => row.join(','))
      ].join('\n')
      
      // Create blob and download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      link.download = `runicorn_experiments_${timestamp}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      
      message.success(t('experiments.export_success', { count: selectedRunData.length }) || `Successfully exported ${selectedRunData.length} runs`)
    } catch (error) {
      logger.error('Export failed:', error)
      message.error(t('experiments.export_failed') || 'Failed to export runs')
    } finally {
      setExportLoading(false)
    }
  }
  
  // Export menu items
  const exportMenuItems = [
    {
      key: 'json',
      icon: <FileTextOutlined />,
      label: t('experiments.export_json') || 'Export as JSON',
      onClick: handleExportJSON,
    },
    {
      key: 'csv',
      icon: <FileExcelOutlined />,
      label: t('experiments.export_csv') || 'Export as CSV',
      onClick: handleExportCSV,
    },
  ]

  // Handle compare action (removed - comparison is done in run detail page)
  const handleCompare = () => {
    if (selectedRowKeys.length < 2) {
      message.warning(t('experiments.select_multiple') || 'Please select at least 2 runs to compare')
      return
    }
    // Open first run with others for comparison
    const firstRun = selectedRowKeys[0]
    navigate(`/runs/${firstRun}`)
    message.info(t('experiments.compare_hint') || 'Use the comparison feature in the run detail page')
  }

  // Enhanced filtering with memoization
  const filteredRuns = useMemo(() => {
    return runs.filter(run => {
      // Search filter - check multiple fields
      const searchLower = searchText.toLowerCase()
      const matchesSearch = searchText === '' || 
        run.run_id.toLowerCase().includes(searchLower) ||
        run.name.toLowerCase().includes(searchLower) ||
        run.project.toLowerCase().includes(searchLower) ||
        (run.summary?.tags && run.summary.tags.some((tag: string) => 
          tag.toLowerCase().includes(searchLower)))
      
      // Project filter
      const matchesProject = projectFilter === 'all' || run.project === projectFilter
      
      // Status filter
      const matchesStatus = statusFilter === 'all' || run.status === statusFilter
      
      return matchesSearch && matchesProject && matchesStatus
    })
  }, [runs, searchText, projectFilter, statusFilter])

  // Enhanced table columns with sorting and better rendering (resizable)
  const columns: ColumnsType<RunData> = useMemo(() => [
    {
      title: t('table.project'),
      dataIndex: 'project',
      key: 'project',
      sorter: (a, b) => a.project.localeCompare(b.project),
      render: (text) => <Tag color="blue">{text}</Tag>,
      width: columnWidths.project,
      onHeaderCell: () => ({
        width: columnWidths.project,
        onResize: handleResize('project'),
      }),
    },
    {
      title: t('table.name'),
      dataIndex: 'name',
      key: 'name',
      width: columnWidths.name,
      sorter: (a, b) => a.name.localeCompare(b.name),
      render: (text, record) => (
        <Tooltip title={`${record.project}/${text}`}>
          <strong>{text}</strong>
        </Tooltip>
      ),
      onHeaderCell: () => ({
        width: columnWidths.name,
        onResize: handleResize('name'),
      }),
    },
    {
      title: t('table.run_id'),
      dataIndex: 'run_id',
      key: 'run_id',
      width: columnWidths.run_id,
      render: (text) => (
        <code style={{ fontSize: '11px', wordBreak: 'break-all' }}>{text}</code>
      ),
      onHeaderCell: () => ({
        width: columnWidths.run_id,
        onResize: handleResize('run_id'),
      }),
    },
    {
      title: t('table.status'),
      dataIndex: 'status',
      key: 'status',
      width: columnWidths.status,
      sorter: (a, b) => a.status.localeCompare(b.status),
      onHeaderCell: () => ({
        width: columnWidths.status,
        onResize: handleResize('status'),
      }),
      render: (status, record) => {
        return <AnimatedStatusBadge status={status} />
      },
    },
    {
      title: t('table.created'),
      dataIndex: 'created',
      key: 'created',
      width: columnWidths.created,
      sorter: (a, b) => new Date(a.created).getTime() - new Date(b.created).getTime(),
      render: (text) => {
        const date = new Date(text)
        // 使用当前语言设置
        const locale = i18n.language === 'zh' ? 'zh-CN' : 'en-US'
        return (
          <span style={{ fontSize: '13px', whiteSpace: 'nowrap' }}>
            {date.toLocaleString(locale, {
              year: 'numeric',
              month: '2-digit',
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              hour12: false
            })}
          </span>
        )
      },
      onHeaderCell: () => ({
        width: columnWidths.created,
        onResize: handleResize('created'),
      }),
    },
    {
      title: t('experiments.best_metric') || 'Best Metric',
      key: 'best_metric',
      width: columnWidths.best_metric,
      onHeaderCell: () => ({
        width: columnWidths.best_metric,
        onResize: handleResize('best_metric'),
      }),
      render: (_, record) => {
        const value = record.best_metric_value
        const name = record.best_metric_name
        if (value != null && name) {
          return (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '13px', color: '#666', fontWeight: 500 }}>{name}</span>
              <span style={{ fontSize: '16px', fontWeight: 700, color: '#1677ff' }}>{value.toFixed(4)}</span>
            </div>
          )
        }
        return '-'
      },
    },
    {
      title: t('experiments.assets') || 'Assets',
      key: 'assets',
      width: columnWidths.assets,
      onHeaderCell: () => ({
        width: columnWidths.assets,
        onResize: handleResize('assets'),
      }),
      render: (_, record) => {
        const count = record.assets_count || 0
        if (count === 0) {
          return <span style={{ color: '#999' }}>-</span>
        }
        return (
          <Tooltip title={t('experiments.assets_tip', { count })}>
            <Badge count={count} style={{ backgroundColor: '#52c41a' }} />
          </Tooltip>
        )
      },
    },
    {
      title: t('table.actions'),
      key: 'actions',
      width: columnWidths.actions,
      onHeaderCell: () => ({
        width: columnWidths.actions,
        onResize: handleResize('actions'),
      }),
      render: (_, record) => (
        <Space size="small">
          <Tooltip title={t('table.view')}>
            <Button 
              type="link" 
              icon={<EyeOutlined />} 
              onClick={() => navigate(`/runs/${record.run_id}`)}
            />
          </Tooltip>
          <Tooltip title={t('experiments.delete') || 'Delete'}>
            <Button 
              type="link" 
              danger 
              icon={<DeleteOutlined />}
              onClick={() => {
                setSelectedRowKeys([record.run_id])
                handleDelete()
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ], [t, navigate, columnWidths, handleResize, handleDelete])

  // Show skeleton on initial load
  if (loading && runs.length === 0) {
    return <ExperimentListSkeleton />
  }

  return (
    <>
      {ConfettiComponent}
      
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={{ padding: 24 }}
      >
        {/* Fancy page title */}
        <motion.div
          initial={experimentsPageConfig.title.initial}
          animate={experimentsPageConfig.title.animate}
          transition={experimentsPageConfig.title.transition}
          style={{ marginBottom: 36 }}
        >
          <h1 style={{
            fontSize: experimentsPageConfig.title.fontSize,
            fontWeight: experimentsPageConfig.title.fontWeight,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            marginBottom: experimentsPageConfig.title.marginBottom,
            lineHeight: experimentsPageConfig.title.lineHeight
          }}>
            {t('menu.experiments')}
          </h1>
          <p style={{
            color: experimentsPageConfig.subtitle.color,
            fontSize: experimentsPageConfig.subtitle.fontSize,
            margin: 0,
            fontWeight: experimentsPageConfig.subtitle.fontWeight
          }}>
            {t('experiments.subtitle')}
          </p>
        </motion.div>
        
        {/* Fancy Statistics Cards with stagger animation */}
        <StaggerContainer>
          <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
            <Col xs={24} sm={12} lg={6}>
              <StaggerItem>
                <FancyStatCard
                  title={t('experiments.total_runs') || 'Total Runs'}
                  value={stats.total}
                  icon={<ExperimentOutlined />}
                  gradientColors={experimentsPageConfig.statCards.total.gradientColors}
                  delay={experimentsPageConfig.statCards.total.delay}
                  pulse={experimentsPageConfig.statCards.total.pulse}
                />
              </StaggerItem>
            </Col>
            
            <Col xs={24} sm={12} lg={6}>
              <StaggerItem>
                <FancyStatCard
                  title={t('experiments.running') || 'Running'}
                  value={stats.running}
                  icon={<ThunderboltOutlined />}
                  gradientColors={experimentsPageConfig.statCards.running.gradientColors}
                  delay={experimentsPageConfig.statCards.running.delay}
                  pulse={stats.running > 0}  // Dynamic based on actual running count
                />
              </StaggerItem>
            </Col>
            
            <Col xs={24} sm={12} lg={6}>
              <StaggerItem>
                <FancyStatCard
                  title={t('experiments.finished') || 'Finished'}
                  value={stats.finished}
                  icon={<CheckCircleOutlined />}
                  gradientColors={experimentsPageConfig.statCards.finished.gradientColors}
                  delay={experimentsPageConfig.statCards.finished.delay}
                  pulse={experimentsPageConfig.statCards.finished.pulse}
                />
              </StaggerItem>
            </Col>
            
            <Col xs={24} sm={12} lg={6}>
              <StaggerItem>
                <FancyStatCard
                  title={t('experiments.failed') || 'Failed'}
                  value={stats.failed}
                  icon={<CloseCircleOutlined />}
                  gradientColors={experimentsPageConfig.statCards.failed.gradientColors}
                  delay={experimentsPageConfig.statCards.failed.delay}
                  pulse={experimentsPageConfig.statCards.failed.pulse}
                />
              </StaggerItem>
            </Col>
          </Row>
        </StaggerContainer>

      {/* Filters and Actions */}
      <motion.div
        initial={experimentsPageConfig.filterCard.animation.initial}
        animate={experimentsPageConfig.filterCard.animation.animate}
        transition={experimentsPageConfig.filterCard.animation.transition}
      >
        <Card
          bordered={false}
          style={{
            borderRadius: experimentsPageConfig.filterCard.borderRadius,
            marginBottom: 20,
            background: experimentsPageConfig.filterCard.background,
            backdropFilter: experimentsPageConfig.filterCard.backdropFilter,
            border: experimentsPageConfig.filterCard.border,
            boxShadow: experimentsPageConfig.filterCard.boxShadow
          }}
          bodyStyle={{ padding: experimentsPageConfig.filterCard.padding }}
        >
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Space>
          <Input
            placeholder={t('experiments.search_placeholder') || 'Search runs...'}
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 200 }}
          />
          <Select
            value={projectFilter}
            onChange={setProjectFilter}
            style={{ width: 150 }}
          >
            <Select.Option value="all">{t('runs.filter.all')}</Select.Option>
            {projects.map(p => (
              <Select.Option key={p} value={p}>{p}</Select.Option>
            ))}
          </Select>
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            style={{ width: 120 }}
          >
            <Select.Option value="all">{t('runs.filter.all')}</Select.Option>
            <Select.Option value="running">{t('experiments.running') || 'Running'}</Select.Option>
            <Select.Option value="finished">{t('experiments.finished') || 'Finished'}</Select.Option>
            <Select.Option value="failed">{t('experiments.failed') || 'Failed'}</Select.Option>
          </Select>
          <Button 
            icon={autoRefresh ? <SyncOutlined spin /> : <ReloadOutlined />} 
            onClick={() => fetchRuns(true)}
            loading={loading}
          >
            {autoRefresh ? t('runs.refreshing') : t('runs.refresh')}
          </Button>
          <Tooltip title={t('experiments.check_status_tooltip') || 'Check if running experiments are still alive'}>
            <Button 
              icon={<HeartOutlined />}
              onClick={handleStatusCheck}
              loading={statusCheckLoading}
              type="dashed"
            >
              {t('experiments.check_status') || 'Check Status'}
            </Button>
          </Tooltip>
          <Checkbox
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
          >
            {t('experiments.auto_refresh') || 'Auto-refresh'}
          </Checkbox>
          <Tooltip title={t('recycle_bin.tooltip') || 'View and restore deleted experiments'}>
            <Button 
              icon={<UndoOutlined />}
              onClick={() => setRecycleBinOpen(true)}
              type="dashed"
            >
              {t('recycle_bin.title') || 'Recycle Bin'}
            </Button>
          </Tooltip>
        </Space>
        
        <Space>
          {selectedRowKeys.length > 0 && (
            <>
              <Button 
                icon={<LineChartOutlined />} 
                onClick={handleCompare}
                disabled={selectedRowKeys.length < 2}
              >
                {t('experiments.compare') || 'Compare'} ({selectedRowKeys.length})
              </Button>
              <Dropdown
                menu={{ items: exportMenuItems }}
                trigger={['click']}
              >
                <Button icon={<ExportOutlined />}>
                  {t('experiments.export') || 'Export'} ({selectedRowKeys.length}) <DownOutlined />
                </Button>
              </Dropdown>
              <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
                {t('experiments.delete') || 'Delete'} ({selectedRowKeys.length})
              </Button>
            </>
          )}
            </Space>
          </Space>
        </Card>
      </motion.div>

      {/* Enhanced Runs Table with fancy effects */}
      <motion.div
        initial={experimentsPageConfig.tableContainer.animation.initial}
        animate={experimentsPageConfig.tableContainer.animation.animate}
        transition={experimentsPageConfig.tableContainer.animation.transition}
      >
        <Card
          bordered={false}
          style={{
            borderRadius: experimentsPageConfig.tableContainer.borderRadius,
            overflow: 'hidden',
            boxShadow: experimentsPageConfig.tableContainer.boxShadow
          }}
          bodyStyle={{ padding: 0 }}
        >
          <Table
            className="enhanced-table"
        components={{
          header: {
            cell: ResizableTitle,
          },
        }}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys as string[]),
          getCheckboxProps: (record) => ({
            disabled: deleteLoading,  // Disable selection during deletion
          }),
        }}
        columns={columns}
        dataSource={filteredRuns}
        rowKey="run_id"
        loading={loading}
        pagination={{
          pageSize: pageSize,
          showSizeChanger: true,
          showQuickJumper: true,
          pageSizeOptions: ['10', '20', '50', '100'],
          onShowSizeChange: (_, size) => setPageSize(size),
          showTotal: (total, range) => 
            t('experiments.table_total', { 
              from: range[0], 
              to: range[1], 
              total 
            }) || `${range[0]}-${range[1]} of ${total} items`,
        }}
        scroll={{ x: 1200 }}  // Horizontal scroll for better mobile view
        size="middle"
        onChange={(pagination, filters, sorter) => {
          setSortedInfo(sorter as SorterResult<RunData>)
        }}
        locale={{
          emptyText: (
            <FancyEmpty
              title={t('experiments.no_runs') || 'No experiments yet'}
              description={t('experiments.no_runs_desc') || 'Start tracking your ML experiments with Runicorn SDK. Check out the quickstart guide to begin.'}
              actionText={t('experiments.view_quickstart') || 'View Quickstart Guide'}
              onAction={() => window.open('https://github.com/runicorn/runicorn#quick-start', '_blank')}
            />
          ),
        }}
      />
        </Card>
      </motion.div>
      
        <RecycleBin
          open={recycleBinOpen}
          onClose={() => setRecycleBinOpen(false)}
          onRestore={() => fetchRuns(false)}
        />
      </motion.div>
    </>
  )
}

export default ExperimentPage
