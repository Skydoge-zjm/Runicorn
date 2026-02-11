import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Table, Button, Card, Space, Input, Select, Tag, Statistic, message, Modal, Tooltip, Empty, Dropdown, Badge, Checkbox, notification, theme } from 'antd'
import { SearchOutlined, ReloadOutlined, DeleteOutlined, ExportOutlined, LineChartOutlined, EyeOutlined, DownOutlined, FileExcelOutlined, FileTextOutlined, FilterOutlined, SyncOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, FilePdfOutlined, HeartOutlined, UndoOutlined, ExperimentOutlined, ThunderboltOutlined, MenuFoldOutlined, MenuUnfoldOutlined, CopyOutlined, PlusOutlined, CloseOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Resizable, ResizeCallbackData as ResizableCallbackData } from 'react-resizable'
import { useSettings } from '../contexts/SettingsContext'
import { checkAllStatus, softDeleteRuns, getStepMetrics, getRunDetail, updateRunAlias, updateRunTags } from '../api'
import RecycleBin from '../components/RecycleBin'
import PathTreePanel from '../components/PathTreePanel'
import AddTagModal from '../components/AddTagModal'
import CompareRunsPanel, { CompareRunInfo } from '../components/CompareRunsPanel'
import CompareChartsView from '../components/CompareChartsView'
import { ExperimentListSkeleton } from '../components/LoadingSkeleton'
import ResizableTitle from '../components/ResizableTitle'
import { useColumnWidths } from '../hooks/useColumnWidths'
import FancyEmpty from '../components/fancy/FancyEmpty'
import AnimatedStatusBadge from '../components/fancy/AnimatedStatusBadge'
import { useSuccessConfetti } from '../hooks/useSuccessConfetti'
import logger from '../utils/logger'
import type { ColumnsType, TableProps } from 'antd/es/table'
import type { SorterResult } from 'antd/es/table/interface'
import type { MetricsData } from '../components/MetricChart'
import '../styles/resizable-table.css'
import '../styles/enhanced-table.css'

// ECharts default color palette
const ECHARTS_COLORS = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
  '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'
]

// Define ResizeCallbackData type locally
interface ResizeCallbackData {
  size: { width: number }
}

interface RunData {
  run_id: string
  path: string
  alias: string | null
  tags: string[]
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
  const location = useLocation()
  const { settings, setSettings } = useSettings()
  const { token } = theme.useToken()
  const [runs, setRuns] = useState<RunData[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([])
  const [searchText, setSearchText] = useState('')
  const [projectFilter, setProjectFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [projects, setProjects] = useState<string[]>([])
  const [stats, setStats] = useState({ total: 0, running: 0, finished: 0, failed: 0 })
  // Use ref for interval to avoid stale closure issues in cleanup
  const refreshIntervalRef = useRef<number | null>(null)
  
  // Use global settings for autoRefresh
  const autoRefresh = settings.autoRefresh
  const setAutoRefresh = (checked: boolean) => {
    setSettings({ ...settings, autoRefresh: checked })
  }
  // Column width management
  const defaultColumnWidths = {
    path: 180,
    alias: 120,
    tags: 180,
    run_id: 140,          // Compact: only show hash suffix with copy button
    status: 100,
    created: 210,         // Wider to show full datetime (2025/10/09 08:26:32)
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
  
  // Inline editing state for alias
  const [editingRunId, setEditingRunId] = useState<string | null>(null)
  const [editingAlias, setEditingAlias] = useState<string>('')
  const [aliasUpdateLoading, setAliasUpdateLoading] = useState(false)
  
  // Path tree panel state
  const [treePanelCollapsed, setTreePanelCollapsed] = useState(() => {
    const saved = localStorage.getItem('tree_panel_collapsed')
    return saved === 'true'
  })
  const [treePanelWidth, setTreePanelWidth] = useState(() => {
    const saved = localStorage.getItem('tree_panel_width')
    return saved ? parseInt(saved, 10) : 240
  })
  const [isResizing, setIsResizing] = useState(false)
  const [selectedTreePath, setSelectedTreePath] = useState<string | null>(null)
  
  // Tag editing state
  const [tagEditingRunId, setTagEditingRunId] = useState<string | null>(null)
  const [tagModalOpen, setTagModalOpen] = useState(false)
  const [tagModalRunId, setTagModalRunId] = useState<string | null>(null)
  const [tagModalCurrentTags, setTagModalCurrentTags] = useState<string[]>([])
  
  // Compare mode state
  const [compareMode, setCompareMode] = useState(false)
  const [compareRunInfos, setCompareRunInfos] = useState<CompareRunInfo[]>([])
  const [compareMetrics, setCompareMetrics] = useState<Map<string, MetricsData>>(new Map())
  const [compareRunLabels, setCompareRunLabels] = useState<Map<string, string>>(new Map())
  const [compareLoading, setCompareLoading] = useState(false)
  const [visibleRunIds, setVisibleRunIds] = useState<Set<string>>(new Set())
  const [addRunsModalOpen, setAddRunsModalOpen] = useState(false)
  
  // Persist tree panel collapsed state and width
  useEffect(() => {
    localStorage.setItem('tree_panel_collapsed', String(treePanelCollapsed))
  }, [treePanelCollapsed])
  
  useEffect(() => {
    localStorage.setItem('tree_panel_width', String(treePanelWidth))
  }, [treePanelWidth])
  
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

  // Handle alias inline editing
  const handleAliasEdit = useCallback((runId: string, currentAlias: string | null) => {
    setEditingRunId(runId)
    setEditingAlias(currentAlias || '')
  }, [])
  
  const handleAliasSave = useCallback(async (runId: string) => {
    const newAlias = editingAlias.trim() || null
    setAliasUpdateLoading(true)
    try {
      await updateRunAlias(runId, newAlias)
      // Update local state
      setRuns(prev => prev.map(r => 
        r.run_id === runId ? { ...r, alias: newAlias } : r
      ))
      message.success(t('experiments.alias_updated') || 'Alias updated')
    } catch (error) {
      logger.error('Failed to update alias:', error)
      message.error(t('experiments.alias_update_failed') || 'Failed to update alias')
    } finally {
      setAliasUpdateLoading(false)
      setEditingRunId(null)
      setEditingAlias('')
    }
  }, [editingAlias, t])
  
  const handleAliasCancel = useCallback(() => {
    setEditingRunId(null)
    setEditingAlias('')
  }, [])
  
  // Handle tree panel resize
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
    
    const startX = e.clientX
    const startWidth = treePanelWidth
    
    const handleMouseMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientX - startX
      const newWidth = Math.min(Math.max(startWidth + delta, 160), 400)
      setTreePanelWidth(newWidth)
    }
    
    const handleMouseUp = () => {
      setIsResizing(false)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
    
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [treePanelWidth])
  
  // Handle tags update
  const handleTagsUpdate = useCallback(async (runId: string, newTags: string[]) => {
    try {
      await updateRunTags(runId, newTags)
      // Update local state
      setRuns(prev => prev.map(r => 
        r.run_id === runId ? { ...r, tags: newTags } : r
      ))
      message.success(t('experiments.tags_updated') || 'Tags updated')
    } catch (error) {
      logger.error('Failed to update tags:', error)
      message.error(t('experiments.tags_update_failed') || 'Failed to update tags')
    }
  }, [t])
  
  // Handle removing a single tag
  const handleRemoveTag = useCallback((runId: string, tagToRemove: string, currentTags: string[]) => {
    const newTags = currentTags.filter(t => t !== tagToRemove)
    handleTagsUpdate(runId, newTags)
  }, [handleTagsUpdate])
  
  // Open tag modal
  const handleOpenTagModal = useCallback((runId: string, currentTags: string[]) => {
    setTagModalRunId(runId)
    setTagModalCurrentTags(currentTags)
    setTagModalOpen(true)
  }, [])
  
  // Handle adding a new tag from modal
  const handleAddTagFromModal = useCallback((tag: string) => {
    if (!tagModalRunId) return
    const newTags = [...tagModalCurrentTags, tag]
    handleTagsUpdate(tagModalRunId, newTags)
    setTagModalOpen(false)
    setTagModalRunId(null)
    setTagModalCurrentTags([])
  }, [tagModalRunId, tagModalCurrentTags, handleTagsUpdate])
  
  // Get all tags from all runs for history
  const allTagsFromRuns = useMemo(() => {
    return runs.flatMap(r => r.tags || [])
  }, [runs])

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
      const runsData = Array.isArray(data) ? data : (data.runs || [])
      
      // Map API response to our RunData interface
      const mappedRuns = runsData.map((r: any) => {
        const created = r.created_time ? new Date(r.created_time * 1000) : new Date()
        
        return {
          run_id: r.id || r.run_id,
          path: r.path || 'default',
          alias: r.alias || null,
          tags: r.tags || [],
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
      
      // Extract unique paths (top-level segments for filtering)
      const uniquePaths = [...new Set(mappedRuns.map((r: RunData) => r.path.split('/')[0]))] as string[]
      setProjects(uniquePaths)
      
      // Calculate statistics
      const runStats = {
        total: mappedRuns.length,
        running: mappedRuns.filter((r: RunData) => r.status === 'running').length,
        finished: mappedRuns.filter((r: RunData) => r.status === 'finished').length,
        failed: mappedRuns.filter((r: RunData) => r.status === 'failed').length,
      }
      setStats(runStats)
    } catch (error) {
      logger.error('Failed to fetch runs:', error)
      if (showLoading) {
        message.error(t('experiments.fetch_failed') || 'Failed to fetch runs')
      }
    }
    if (showLoading) setLoading(false)
  }, [t])

  // Fetch runs on mount and when navigating back to this page
  useEffect(() => {
    fetchRuns(true)
  }, [location.key])

  // Batch delete runs by path
  const handleBatchDeleteByPath = useCallback(async (path: string) => {
    try {
      const response = await fetch('/api/paths/soft-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const result = await response.json()
      if (result.deleted_count > 0) {
        triggerConfetti()
        message.success(t('experiments.soft_delete_success', { count: result.deleted_count }) || `Moved ${result.deleted_count} runs to recycle bin`)
        fetchRuns(false)
      } else {
        message.info(t('experiments.no_runs_to_delete') || 'No runs to delete in this path')
      }
    } catch (error) {
      logger.error('Batch delete by path failed:', error)
      message.error(t('experiments.delete_failed') || 'Failed to delete runs')
    }
  }, [t, fetchRuns, triggerConfetti])
  
  // Batch export runs by path
  const handleBatchExportByPath = useCallback(async (path: string) => {
    try {
      // Download as ZIP file
      const url = `/api/paths/export?path=${encodeURIComponent(path)}&format=zip`
      const link = document.createElement('a')
      link.href = url
      link.download = `runicorn_export_${path.replace(/\//g, '_')}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      message.success(t('experiments.export_started') || 'Export started')
    } catch (error) {
      logger.error('Batch export by path failed:', error)
      message.error(t('experiments.export_failed') || 'Failed to export runs')
    }
  }, [t])

  // Auto-refresh functionality using global settings
  useEffect(() => {
    // Clear any existing interval first
    if (refreshIntervalRef.current) {
      window.clearInterval(refreshIntervalRef.current)
      refreshIntervalRef.current = null
    }
    
    if (autoRefresh) {
      refreshIntervalRef.current = window.setInterval(() => {
        fetchRuns(false)  // Don't show loading for auto-refresh
      }, settings.refreshInterval * 1000)
    }
    
    return () => {
      if (refreshIntervalRef.current) {
        window.clearInterval(refreshIntervalRef.current)
        refreshIntervalRef.current = null
      }
    }
  }, [autoRefresh, settings.refreshInterval, fetchRuns])

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
          <p style={{ color: token.colorPrimary, fontWeight: 500 }}>
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
          path: run.path,
          alias: run.alias,
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
        'Run ID', 'Path', 'Alias', 'Status', 'Created Time',
        'Final Loss', 'Learning Rate', 'Batch Size', 'Epochs',
        'Best Metric Value', 'Best Metric Name'
      ]
      
      // Create CSV rows with safe escaping
      const rows = selectedRunData.map(run => [
        csvEscape(run.run_id),
        csvEscape(run.path),
        csvEscape(run.alias),
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

  // Handle compare action - switch to inline compare mode
  const handleCompare = useCallback(async () => {
    if (selectedRowKeys.length < 2) {
      message.warning(t('experiments.select_multiple') || 'Please select at least 2 runs to compare')
      return
    }
    
    // Build run info list from selected runs
    const selectedRuns = runs.filter(r => selectedRowKeys.includes(r.run_id))
    const runInfos: CompareRunInfo[] = selectedRuns.map(r => ({
      runId: r.run_id,
      path: r.path,
      alias: r.alias,
      status: r.status,
    }))
    
    // Build labels map (prefer alias, fallback to path last segment)
    const labels = new Map<string, string>()
    selectedRuns.forEach(r => {
      labels.set(r.run_id, r.alias || r.path.split('/').pop() || r.run_id.slice(-12))
    })
    
    setCompareRunInfos(runInfos)
    setCompareRunLabels(labels)
    setCompareMode(true)
    setCompareLoading(true)
    
    // Initialize visible runs (all visible by default)
    setVisibleRunIds(new Set(selectedRowKeys))
    
    // Fetch metrics for all selected runs in parallel
    try {
      const metricsMap = new Map<string, MetricsData>()
      await Promise.all(
        selectedRowKeys.map(async (runId) => {
          try {
            const data = await getStepMetrics(runId)
            metricsMap.set(runId, data)
          } catch (err) {
            logger.warn(`Failed to fetch metrics for ${runId}:`, err)
          }
        })
      )
      setCompareMetrics(metricsMap)
    } catch (error) {
      logger.error('Failed to fetch metrics for comparison:', error)
      message.error(t('experiments.compare_fetch_failed') || 'Failed to load metrics')
    } finally {
      setCompareLoading(false)
    }
  }, [selectedRowKeys, runs, t])
  
  // Toggle run visibility in compare charts
  const toggleRunVisibility = useCallback((runId: string) => {
    setVisibleRunIds(prev => {
      const next = new Set(prev)
      if (next.has(runId)) {
        next.delete(runId)
      } else {
        next.add(runId)
      }
      return next
    })
  }, [])
  
  // Handle add more runs to comparison
  const handleAddRuns = useCallback(() => {
    setAddRunsModalOpen(true)
  }, [])
  
  // Exit compare mode
  const handleExitCompare = useCallback(() => {
    setCompareMode(false)
    setCompareRunInfos([])
    setCompareMetrics(new Map())
    setCompareRunLabels(new Map())
  }, [])
  
  // Check if any compared run is still running
  const hasRunningCompareRun = useMemo(() => {
    return compareRunInfos.some(r => r.status === 'running')
  }, [compareRunInfos])
  
  // Auto-refresh metrics and status when in compare mode with running experiments
  useEffect(() => {
    if (!compareMode || !hasRunningCompareRun || compareLoading) return
    
    const refreshInterval = settings.refreshInterval * 1000 // Use global refresh interval
    
    const intervalId = window.setInterval(async () => {
      // Only refresh for running runs
      const runningRunIds = compareRunInfos
        .filter(r => r.status === 'running')
        .map(r => r.runId)
      
      if (runningRunIds.length === 0) return
      
      try {
        const newMetrics = new Map(compareMetrics)
        const updatedRunInfos = [...compareRunInfos]
        let statusChanged = false
        
        await Promise.all(
          runningRunIds.map(async (runId) => {
            try {
              // Fetch metrics
              const data = await getStepMetrics(runId)
              newMetrics.set(runId, data)
              
              // Fetch status update
              const detail = await getRunDetail(runId)
              const newStatus = detail.status || 'unknown'
              
              // Update status if changed
              const idx = updatedRunInfos.findIndex(r => r.runId === runId)
              if (idx !== -1 && updatedRunInfos[idx].status !== newStatus) {
                updatedRunInfos[idx] = { ...updatedRunInfos[idx], status: newStatus }
                statusChanged = true
              }
            } catch (err) {
              logger.warn(`Failed to refresh data for ${runId}:`, err)
            }
          })
        )
        
        setCompareMetrics(newMetrics)
        if (statusChanged) {
          setCompareRunInfos(updatedRunInfos)
        }
      } catch (error) {
        logger.error('Failed to refresh compare data:', error)
      }
    }, refreshInterval)
    
    return () => window.clearInterval(intervalId)
  }, [compareMode, hasRunningCompareRun, compareLoading, compareRunInfos, compareMetrics, settings.refreshInterval])

  // Enhanced filtering with memoization
  const filteredRuns = useMemo(() => {
    return runs.filter(run => {
      // Search filter - check multiple fields
      const searchLower = searchText.toLowerCase()
      const matchesSearch = searchText === '' || 
        run.run_id.toLowerCase().includes(searchLower) ||
        run.path.toLowerCase().includes(searchLower) ||
        (run.alias && run.alias.toLowerCase().includes(searchLower)) ||
        (run.tags && run.tags.some((tag: string) => 
          tag.toLowerCase().includes(searchLower)))
      
      // Path filter from tree panel (prefix match)
      const matchesTreePath = !selectedTreePath || 
        run.path === selectedTreePath || 
        run.path.startsWith(`${selectedTreePath}/`)
      
      // Path filter from dropdown (matches top-level segment)
      const topLevelPath = run.path.split('/')[0]
      const matchesProject = projectFilter === 'all' || topLevelPath === projectFilter
      
      // Status filter
      const matchesStatus = statusFilter === 'all' || run.status === statusFilter
      
      return matchesSearch && matchesTreePath && matchesProject && matchesStatus
    })
  }, [runs, searchText, selectedTreePath, projectFilter, statusFilter])

  // Enhanced table columns with sorting and better rendering (resizable)
  const columns: ColumnsType<RunData> = useMemo(() => [
    {
      title: t('table.path'),
      dataIndex: 'path',
      key: 'path',
      sorter: (a, b) => a.path.localeCompare(b.path),
      render: (text) => (
        <Tooltip title={text}>
          <code style={{ fontSize: '12px', color: token.colorPrimary }}>{text}</code>
        </Tooltip>
      ),
      width: columnWidths.path,
      onHeaderCell: () => ({
        width: columnWidths.path,
        onResize: handleResize('path'),
      }),
    },
    {
      title: t('table.alias'),
      dataIndex: 'alias',
      key: 'alias',
      width: columnWidths.alias,
      sorter: (a, b) => (a.alias || '').localeCompare(b.alias || ''),
      render: (text, record) => {
        const isEditing = editingRunId === record.run_id
        
        if (isEditing) {
          return (
            <Input
              size="small"
              value={editingAlias}
              onChange={(e) => setEditingAlias(e.target.value)}
              onPressEnter={() => handleAliasSave(record.run_id)}
              onBlur={() => handleAliasSave(record.run_id)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  handleAliasCancel()
                }
              }}
              autoFocus
              style={{ width: '100%' }}
              placeholder={t('experiments.alias_placeholder') || 'Enter alias...'}
              disabled={aliasUpdateLoading}
            />
          )
        }
        
        return (
          <Tooltip title={t('experiments.double_click_edit') || 'Double-click to edit'}>
            <div
              style={{ 
                cursor: 'pointer', 
                minHeight: 22,
                display: 'flex',
                alignItems: 'center',
              }}
              onDoubleClick={() => handleAliasEdit(record.run_id, text)}
            >
              {text ? (
                <Tag color="purple">{text}</Tag>
              ) : (
                <span style={{ color: token.colorTextDisabled }}>-</span>
              )}
            </div>
          </Tooltip>
        )
      },
      onHeaderCell: () => ({
        width: columnWidths.alias,
        onResize: handleResize('alias'),
      }),
    },
    {
      title: t('table.tags'),
      dataIndex: 'tags',
      key: 'tags',
      width: columnWidths.tags,
      render: (tags: string[], record) => {
        const currentTags = tags || []
        
        return (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
            {currentTags.map(tag => (
              <Tag
                key={tag}
                closable
                onClose={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  handleRemoveTag(record.run_id, tag, currentTags)
                }}
                style={{ marginRight: 0 }}
              >
                {tag}
              </Tag>
            ))}
            <Tooltip title={t('experiments.add_tag') || 'Add tag'}>
              <Tag
                onClick={(e) => {
                  e.stopPropagation()
                  handleOpenTagModal(record.run_id, currentTags)
                }}
                style={{ 
                  cursor: 'pointer', 
                  borderStyle: 'dashed',
                  background: 'transparent',
                }}
              >
                <PlusOutlined />
              </Tag>
            </Tooltip>
          </div>
        )
      },
      onHeaderCell: () => ({
        width: columnWidths.tags,
        onResize: handleResize('tags'),
      }),
    },
    {
      title: t('table.run_id'),
      dataIndex: 'run_id',
      key: 'run_id',
      width: columnWidths.run_id,
      render: (text: string) => {
        // Extract hash suffix (last segment after underscore)
        const suffix = text.split('_').pop() || text.slice(-6)
        return (
          <Space size={4}>
            <Tooltip title={text}>
              <code style={{ fontSize: '12px', cursor: 'pointer' }}>{suffix}</code>
            </Tooltip>
            <Tooltip title={t('common.copy') || 'Copy'}>
              <Button
                type="text"
                size="small"
                icon={<CopyOutlined style={{ fontSize: 12 }} />}
                style={{ padding: '0 4px', height: 20, minWidth: 20 }}
                onClick={(e) => {
                  e.stopPropagation()
                  navigator.clipboard.writeText(text)
                  message.success(t('common.copied') || 'Copied!')
                }}
              />
            </Tooltip>
          </Space>
        )
      },
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
        // Use current language setting
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
              <span style={{ fontSize: '13px', color: token.colorTextSecondary, fontWeight: 500 }}>{name}</span>
              <span style={{ fontSize: '16px', fontWeight: 700, color: token.colorPrimary }}>{value.toFixed(4)}</span>
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
          return <span style={{ color: token.colorTextDisabled }}>-</span>
        }
        return (
          <Tooltip title={t('experiments.assets_tip', { count })}>
            <Badge count={count} style={{ backgroundColor: token.colorSuccess }} />
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
  ], [t, navigate, columnWidths, handleResize, handleDelete, token, i18n.language, editingRunId, editingAlias, aliasUpdateLoading, handleAliasEdit, handleAliasSave, handleAliasCancel, handleTagsUpdate, handleRemoveTag, handleOpenTagModal])

  // Show skeleton on initial load
  if (loading && runs.length === 0) {
    return <ExperimentListSkeleton />
  }

  return (
    <>
      {ConfettiComponent}
      
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        height: '100%',
        overflow: 'hidden',
        padding: 16,
      }}>
        {/* Header: Title + Stats - fixed height */}
        <div style={{ flexShrink: 0, marginBottom: 12 }}>
          {/* Header: Title + Inline Stats */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12,
          }}>
            <h1 style={{
              fontSize: 20,
              fontWeight: 600,
              color: token.colorText,
              margin: 0,
            }}>
              {t('menu.experiments')}
            </h1>
            
            {/* Inline Statistics */}
            <Space size={16} style={{ flexWrap: 'wrap' }}>
              <span style={{ color: token.colorTextSecondary, fontSize: 13 }}>
                <ExperimentOutlined style={{ marginRight: 4 }} />
                {t('experiments.total_runs') || 'Total'}: <span style={{ fontWeight: 700, fontSize: 15, color: token.colorText }}>{stats.total}</span>
              </span>
              <span style={{ color: token.colorTextSecondary, fontSize: 13 }}>
                <ThunderboltOutlined style={{ marginRight: 4, color: token.colorWarning }} />
                {t('experiments.running') || 'Running'}: <span style={{ fontWeight: 700, fontSize: 15, color: token.colorWarning }}>{stats.running}</span>
              </span>
              <span style={{ color: token.colorTextSecondary, fontSize: 13 }}>
                <CheckCircleOutlined style={{ marginRight: 4, color: token.colorSuccess }} />
                {t('experiments.finished') || 'Finished'}: <span style={{ fontWeight: 700, fontSize: 15, color: token.colorSuccess }}>{stats.finished}</span>
              </span>
              <span style={{ color: token.colorTextSecondary, fontSize: 13 }}>
                <CloseCircleOutlined style={{ marginRight: 4, color: token.colorError }} />
                {t('experiments.failed') || 'Failed'}: <span style={{ fontWeight: 700, fontSize: 15, color: token.colorError }}>{stats.failed}</span>
              </span>
            </Space>
          </div>
        </div>

        {/* Main content: Path Tree + Runs Table - fills remaining space */}
        <div style={{ 
          display: 'flex', 
          gap: 16,
          flex: 1,
          minHeight: 0,  // Important for flex child scrolling
          overflow: 'hidden',
        }}>
          {/* Left: Path Tree Panel OR Compare Runs Panel */}
          {compareMode ? (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              style={{ 
                width: 260, 
                flexShrink: 0,
                borderRadius: 8,
                overflow: 'hidden',
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <CompareRunsPanel
                runs={compareRunInfos}
                colors={ECHARTS_COLORS}
                visibleRunIds={visibleRunIds}
                onToggleRunVisibility={toggleRunVisibility}
                onAddRuns={handleAddRuns}
                onBack={handleExitCompare}
                style={{ height: '100%', minHeight: 0 }}
              />
            </motion.div>
          ) : (
            !treePanelCollapsed && (
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                style={{ 
                  width: treePanelWidth, 
                  flexShrink: 0,
                  borderRadius: 8,
                  overflow: 'hidden',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                  display: 'flex',
                  flexDirection: 'column',
                  position: 'relative',
                }}
              >
                <PathTreePanel
                  selectedPath={selectedTreePath}
                  onSelectPath={setSelectedTreePath}
                  onBatchDelete={handleBatchDeleteByPath}
                  onBatchExport={handleBatchExportByPath}
                  style={{ height: '100%', minHeight: 0 }}
                />
                {/* Resize handle */}
                <div
                  onMouseDown={handleResizeStart}
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: 0,
                    bottom: 0,
                    width: 4,
                    cursor: 'col-resize',
                    background: isResizing ? token.colorPrimary : 'transparent',
                    transition: 'background 0.2s',
                    zIndex: 10,
                  }}
                  onMouseEnter={(e) => {
                    if (!isResizing) {
                      (e.target as HTMLElement).style.background = token.colorPrimaryBg
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isResizing) {
                      (e.target as HTMLElement).style.background = 'transparent'
                    }
                  }}
                />
              </motion.div>
            )
          )}

          {/* Right: Filters + Table OR Compare Charts */}
          <div style={{ 
            flex: 1, 
            minWidth: 0, 
            display: 'flex', 
            flexDirection: 'column', 
            overflow: 'hidden',
            minHeight: 0,
          }}>
            {compareMode ? (
              /* Compare Charts View */
              <CompareChartsView
                runIds={compareRunInfos.map(r => r.runId)}
                visibleRunIds={visibleRunIds}
                metricsMap={compareMetrics}
                runLabels={compareRunLabels}
                colors={ECHARTS_COLORS}
                loading={compareLoading}
              />
            ) : (
              <>
            {/* Filters and Actions - fixed height */}
            <Card
              bordered={false}
              size="small"
              style={{
                borderRadius: 8,
                marginBottom: 12,
                flexShrink: 0,
              }}
              bodyStyle={{ padding: '12px 16px' }}
            >
              <Space style={{ width: '100%', justifyContent: 'space-between', flexWrap: 'wrap' }}>
                <Space wrap>
                  <Tooltip title={treePanelCollapsed ? (t('experiments.show_tree') || 'Show path tree') : (t('experiments.hide_tree') || 'Hide path tree')}>
                    <Button
                      icon={treePanelCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                      onClick={() => setTreePanelCollapsed(!treePanelCollapsed)}
                    />
                  </Tooltip>
                  <Input
                    placeholder={t('experiments.search_placeholder') || 'Search runs...'}
                    prefix={<SearchOutlined />}
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    style={{ width: 180 }}
                    allowClear
                  />
                  <Select
                    value={projectFilter}
                    onChange={setProjectFilter}
                    style={{ width: 140 }}
                    options={[
                      { value: 'all', label: t('experiments.all_projects') || 'All Projects' },
                      ...projects.map(p => ({ value: p, label: p }))
                    ]}
                  />
                  <Select
                    value={statusFilter}
                    onChange={setStatusFilter}
                    style={{ width: 120 }}
                    options={[
                      { value: 'all', label: t('experiments.all_status') || 'All Status' },
                      { value: 'running', label: t('experiments.running') || 'Running' },
                      { value: 'finished', label: t('experiments.finished') || 'Finished' },
                      { value: 'failed', label: t('experiments.failed') || 'Failed' },
                    ]}
                  />
                  <Button
                    icon={autoRefresh ? <SyncOutlined spin /> : <ReloadOutlined />}
                    onClick={() => fetchRuns(true)}
                    loading={loading}
                  >
                    {t('runs.refresh') || 'Refresh'}
                  </Button>
                  <Checkbox
                    checked={autoRefresh}
                    onChange={(e) => setAutoRefresh(e.target.checked)}
                  >
                    {t('experiments.auto_refresh') || 'Auto'}
                  </Checkbox>
                  <Button icon={<UndoOutlined />} onClick={() => setRecycleBinOpen(true)}>
                    {t('experiments.recycle_bin') || 'Bin'}
                  </Button>
                </Space>
                
                <Space>
                  {selectedRowKeys.length > 0 && (
                    <>
                      <Button icon={<LineChartOutlined />} onClick={handleCompare} disabled={selectedRowKeys.length < 2}>
                        {t('experiments.compare') || 'Compare'} ({selectedRowKeys.length})
                      </Button>
                      <Dropdown menu={{ items: exportMenuItems }} trigger={['click']}>
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

            {/* Table - fills remaining space with internal scroll */}
            <Card
              bordered={false}
              style={{
                borderRadius: 8,
                flex: 1,
                minHeight: 0,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
              }}
              bodyStyle={{ padding: 0, flex: 1, minHeight: 0, overflow: 'auto' }}
            >
              <Table
                className="enhanced-table"
                components={{ header: { cell: ResizableTitle } }}
                rowSelection={{
                  selectedRowKeys,
                  onChange: (keys) => setSelectedRowKeys(keys as string[]),
                  getCheckboxProps: () => ({ disabled: deleteLoading }),
                }}
                columns={columns}
                dataSource={filteredRuns}
                rowKey="run_id"
                loading={loading}
                pagination={{
                  pageSize,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  pageSizeOptions: ['10', '20', '50', '100'],
                  onShowSizeChange: (_, size) => setPageSize(size),
                  showTotal: (total, range) => `${range[0]}-${range[1]} / ${total}`,
                }}
                scroll={{ x: 1200 }}
                size="middle"
                onChange={(_, __, sorter) => setSortedInfo(sorter as SorterResult<RunData>)}
                locale={{
                  emptyText: (
                    <FancyEmpty
                      title={t('experiments.no_runs') || 'No experiments yet'}
                      description={t('experiments.no_runs_desc') || 'Start tracking your ML experiments.'}
                      actionText={t('experiments.view_quickstart') || 'View Quickstart'}
                      onAction={() => window.open('https://github.com/runicorn/runicorn#quick-start', '_blank')}
                    />
                  ),
                }}
              />
            </Card>
              </>
            )}
          </div>
        </div>
      </div>
      
      <RecycleBin
        open={recycleBinOpen}
        onClose={() => setRecycleBinOpen(false)}
        onRestore={() => fetchRuns(false)}
      />
      
      <AddTagModal
        open={tagModalOpen}
        existingTags={tagModalCurrentTags}
        allTags={allTagsFromRuns}
        onConfirm={handleAddTagFromModal}
        onClose={() => {
          setTagModalOpen(false)
          setTagModalRunId(null)
          setTagModalCurrentTags([])
        }}
      />
    </>
  )
}

export default ExperimentPage
