import { useState, useCallback, useMemo, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { message } from 'antd'
import { useSettings } from '../contexts/SettingsContext'
import { getStepMetrics, getRunDetail } from '../api'
import type { CompareRunInfo } from '../components/CompareRunsPanel'
import type { MetricsData } from '../components/MetricChart'
import type { RunData } from './useExperimentData'
import logger from '../utils/logger'

export function useCompareMode(runs: RunData[], selectedRowKeys: string[]) {
  const { t } = useTranslation()
  const { settings } = useSettings()
  const [searchParams, setSearchParams] = useSearchParams()

  const compareIdsFromUrl = useMemo(() =>
    searchParams.get('compare')?.split(',').filter(Boolean) || []
  , [searchParams])
  const compareMode = compareIdsFromUrl.length >= 2

  const [compareRunInfos, setCompareRunInfos] = useState<CompareRunInfo[]>([])
  const [compareMetrics, setCompareMetrics] = useState<Map<string, MetricsData>>(new Map())
  const [compareRunLabels, setCompareRunLabels] = useState<Map<string, string>>(new Map())
  const [compareLoading, setCompareLoading] = useState(false)
  const [visibleRunIds, setVisibleRunIds] = useState<Set<string>>(new Set())

  // Restore compare state from URL
  useEffect(() => {
    if (compareIdsFromUrl.length >= 2 && compareRunInfos.length === 0 && runs.length > 0) {
      const selectedRuns = runs.filter(r => compareIdsFromUrl.includes(r.run_id))
      if (selectedRuns.length < 2) return
      const runInfos: CompareRunInfo[] = selectedRuns.map(r => ({
        runId: r.run_id, path: r.path, alias: r.alias, status: r.status,
      }))
      const labels = new Map<string, string>()
      selectedRuns.forEach(r => {
        labels.set(r.run_id, r.alias || r.path.split('/').pop() || r.run_id.slice(-12))
      })
      setCompareRunInfos(runInfos)
      setCompareRunLabels(labels)
      setVisibleRunIds(new Set(compareIdsFromUrl))
      setCompareLoading(true)
      Promise.all(
        compareIdsFromUrl.map(async (runId) => {
          try { return [runId, await getStepMetrics(runId)] as const }
          catch { return null }
        })
      ).then(results => {
        const metricsMap = new Map<string, MetricsData>()
        for (const r of results) { if (r) metricsMap.set(r[0], r[1]) }
        setCompareMetrics(metricsMap)
      }).finally(() => setCompareLoading(false))
    }
  }, [compareIdsFromUrl, runs])

  const handleCompare = useCallback(async () => {
    if (selectedRowKeys.length < 2) {
      message.warning(t('experiments.select_multiple'))
      return
    }
    const selectedRuns = runs.filter(r => selectedRowKeys.includes(r.run_id))
    const runInfos: CompareRunInfo[] = selectedRuns.map(r => ({
      runId: r.run_id, path: r.path, alias: r.alias, status: r.status,
    }))
    const labels = new Map<string, string>()
    selectedRuns.forEach(r => {
      labels.set(r.run_id, r.alias || r.path.split('/').pop() || r.run_id.slice(-12))
    })
    setCompareRunInfos(runInfos)
    setCompareRunLabels(labels)
    setSearchParams({ compare: selectedRowKeys.join(',') })
    setCompareLoading(true)
    setVisibleRunIds(new Set(selectedRowKeys))

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
      message.error(t('experiments.compare_fetch_failed'))
    } finally {
      setCompareLoading(false)
    }
  }, [selectedRowKeys, runs, t])

  const toggleRunVisibility = useCallback((runId: string) => {
    setVisibleRunIds(prev => {
      const next = new Set(prev)
      if (next.has(runId)) next.delete(runId)
      else next.add(runId)
      return next
    })
  }, [])

  const handleAddRuns = useCallback(() => {
    message.info(t('experiments.add_runs_coming_soon'))
  }, [t])

  const handleExitCompare = useCallback(() => {
    setSearchParams(prev => { prev.delete('compare'); return prev })
    setCompareRunInfos([])
    setCompareMetrics(new Map())
    setCompareRunLabels(new Map())
  }, [setSearchParams])

  const hasRunningCompareRun = useMemo(() => {
    return compareRunInfos.some(r => r.status === 'running')
  }, [compareRunInfos])

  // Auto-refresh metrics for running compare runs
  useEffect(() => {
    if (!compareMode || !hasRunningCompareRun || compareLoading) return
    const interval = settings.refreshInterval * 1000

    const intervalId = window.setInterval(async () => {
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
              const data = await getStepMetrics(runId)
              newMetrics.set(runId, data)
              const detail = await getRunDetail(runId)
              const newStatus = detail.status || 'unknown'
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
        if (statusChanged) setCompareRunInfos(updatedRunInfos)
      } catch (error) {
        logger.error('Failed to refresh compare data:', error)
      }
    }, interval)

    return () => window.clearInterval(intervalId)
  }, [compareMode, hasRunningCompareRun, compareLoading, compareRunInfos, compareMetrics, settings.refreshInterval])

  return {
    compareMode, compareIdsFromUrl,
    compareRunInfos, compareMetrics, compareRunLabels,
    compareLoading, visibleRunIds,
    handleCompare, handleExitCompare,
    toggleRunVisibility, handleAddRuns,
  }
}
