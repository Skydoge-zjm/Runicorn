import { useState, useCallback, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { App } from 'antd'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useSettings } from '../contexts/SettingsContext'
import { listRuns, softDeleteByPath as apiSoftDeleteByPath } from '../api'
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

/** Map raw API response to RunData[] */
function mapRuns(data: any): RunData[] {
  const runsData = Array.isArray(data) ? data : (data.runs || [])
  return runsData.map((r: any) => {
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
}

export function useExperimentData(_locationKey: string) {
  const { t } = useTranslation()
  const { message } = App.useApp()
  const { settings, setSettings } = useSettings()
  const queryClient = useQueryClient()
  const autoRefresh = settings.autoRefresh
  const setAutoRefresh = (checked: boolean) => {
    setSettings({ ...settings, autoRefresh: checked })
  }

  // React Query for runs list — replaces manual fetch + setInterval
  const { data: queryRuns, isLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: async () => mapRuns(await listRuns()),
    refetchInterval: autoRefresh ? settings.refreshInterval * 1000 : false,
    refetchOnWindowFocus: true,
  })

  // Local state for optimistic updates (inline alias / tag edits)
  const [runs, setRuns] = useState<RunData[]>([])
  useEffect(() => {
    if (queryRuns) setRuns(queryRuns)
  }, [queryRuns])

  const loading = isLoading

  // Derived data
  const projects = useMemo(() => {
    return [...new Set(runs.map(r => r.path.split('/')[0]))] as string[]
  }, [runs])

  const stats = useMemo<RunStats>(() => ({
    total: runs.length,
    running: runs.filter(r => r.status === 'running').length,
    finished: runs.filter(r => r.status === 'finished').length,
    failed: runs.filter(r => r.status === 'failed').length,
  }), [runs])

  // Manual refetch (used by Refresh button / after mutations)
  const fetchRuns = useCallback(async (_showLoading?: boolean) => {
    await queryClient.invalidateQueries({ queryKey: ['runs'] })
  }, [queryClient])

  const handleBatchDeleteByPath = useCallback(async (path: string) => {
    try {
      const result = await apiSoftDeleteByPath(path)
      if (result.deleted_count > 0) {
        message.success(t('experiments.soft_delete_success', { count: result.deleted_count }))
        fetchRuns(false)
      } else {
        message.info(t('experiments.no_runs_to_delete'))
      }
    } catch (error) {
      logger.error('Batch delete by path failed:', error)
      message.error(t('experiments.delete_failed'))
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
      message.success(t('experiments.export_started'))
    } catch (error) {
      logger.error('Batch export by path failed:', error)
      message.error(t('experiments.export_failed'))
    }
  }, [t])

  return {
    runs, setRuns, loading, projects, stats,
    autoRefresh, setAutoRefresh,
    fetchRuns,
    handleBatchDeleteByPath, handleBatchExportByPath,
  }
}
