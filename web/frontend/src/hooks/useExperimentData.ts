import { useState, useCallback, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { message } from 'antd'
import { useSettings } from '../contexts/SettingsContext'
import { listRuns, checkAllStatus, softDeleteByPath as apiSoftDeleteByPath } from '../api'
import logger from '../utils/logger'

export interface RunData {
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

export interface RunStats {
  total: number
  running: number
  finished: number
  failed: number
}

export function useExperimentData(locationKey: string) {
  const { t } = useTranslation()
  const { settings, setSettings } = useSettings()
  const [runs, setRuns] = useState<RunData[]>([])
  const [loading, setLoading] = useState(false)
  const [projects, setProjects] = useState<string[]>([])
  const [stats, setStats] = useState<RunStats>({ total: 0, running: 0, finished: 0, failed: 0 })
  const refreshIntervalRef = useRef<number | null>(null)
  const [statusCheckLoading, setStatusCheckLoading] = useState(false)

  const autoRefresh = settings.autoRefresh
  const setAutoRefresh = (checked: boolean) => {
    setSettings({ ...settings, autoRefresh: checked })
  }

  const fetchRuns = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true)
    try {
      const data = await listRuns()
      const runsData = Array.isArray(data) ? data : (data.runs || [])

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
          assets_count: r.assets_count || 0,
        }
      })

      setRuns(mappedRuns)
      const uniquePaths = [...new Set(mappedRuns.map((r: RunData) => r.path.split('/')[0]))] as string[]
      setProjects(uniquePaths)

      setStats({
        total: mappedRuns.length,
        running: mappedRuns.filter((r: RunData) => r.status === 'running').length,
        finished: mappedRuns.filter((r: RunData) => r.status === 'finished').length,
        failed: mappedRuns.filter((r: RunData) => r.status === 'failed').length,
      })
    } catch (error) {
      logger.error('Failed to fetch runs:', error)
      if (showLoading) message.error(t('experiments.fetch_failed') || 'Failed to fetch runs')
    }
    if (showLoading) setLoading(false)
  }, [t])

  // Fetch on mount / navigation
  useEffect(() => { fetchRuns(true) }, [locationKey])

  // Auto-refresh
  useEffect(() => {
    if (refreshIntervalRef.current) {
      window.clearInterval(refreshIntervalRef.current)
      refreshIntervalRef.current = null
    }
    if (autoRefresh) {
      refreshIntervalRef.current = window.setInterval(() => {
        fetchRuns(false)
      }, settings.refreshInterval * 1000)
    }
    return () => {
      if (refreshIntervalRef.current) {
        window.clearInterval(refreshIntervalRef.current)
        refreshIntervalRef.current = null
      }
    }
  }, [autoRefresh, settings.refreshInterval, fetchRuns])

  const handleStatusCheck = useCallback(async () => {
    setStatusCheckLoading(true)
    try {
      const result = await checkAllStatus()
      if (result.updated > 0) {
        message.success(`Updated ${result.updated} experiment statuses`)
        fetchRuns(false)
      } else {
        message.info('All experiment statuses are up to date')
      }
    } catch (error) {
      logger.error('Status check failed:', error)
      message.error('Failed to check experiment statuses')
    } finally {
      setStatusCheckLoading(false)
    }
  }, [fetchRuns])

  const handleBatchDeleteByPath = useCallback(async (path: string) => {
    try {
      const result = await apiSoftDeleteByPath(path)
      if (result.deleted_count > 0) {
        message.success(t('experiments.soft_delete_success', { count: result.deleted_count }) || `Moved ${result.deleted_count} runs to recycle bin`)
        fetchRuns(false)
      } else {
        message.info(t('experiments.no_runs_to_delete') || 'No runs to delete in this path')
      }
    } catch (error) {
      logger.error('Batch delete by path failed:', error)
      message.error(t('experiments.delete_failed') || 'Failed to delete runs')
    }
  }, [t, fetchRuns])

  const handleBatchExportByPath = useCallback(async (path: string) => {
    try {
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

  return {
    runs, setRuns, loading, projects, stats,
    autoRefresh, setAutoRefresh,
    fetchRuns, statusCheckLoading, handleStatusCheck,
    handleBatchDeleteByPath, handleBatchExportByPath,
  }
}
