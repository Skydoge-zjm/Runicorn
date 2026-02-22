import { useState, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { message } from 'antd'
import { updateRunAlias, updateRunTags } from '../api'
import type { RunData } from './useExperimentData'
import logger from '../utils/logger'

export function useInlineEditing(
  runs: RunData[],
  setRuns: React.Dispatch<React.SetStateAction<RunData[]>>
) {
  const { t } = useTranslation()

  // Alias editing
  const [editingRunId, setEditingRunId] = useState<string | null>(null)
  const [editingAlias, setEditingAlias] = useState<string>('')
  const [aliasUpdateLoading, setAliasUpdateLoading] = useState(false)

  const handleAliasEdit = useCallback((runId: string, currentAlias: string | null) => {
    setEditingRunId(runId)
    setEditingAlias(currentAlias || '')
  }, [])

  const handleAliasSave = useCallback(async (runId: string) => {
    const newAlias = editingAlias.trim() || null
    setAliasUpdateLoading(true)
    try {
      await updateRunAlias(runId, newAlias)
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
  }, [editingAlias, t, setRuns])

  const handleAliasCancel = useCallback(() => {
    setEditingRunId(null)
    setEditingAlias('')
  }, [])

  // Tag editing
  const [tagModalOpen, setTagModalOpen] = useState(false)
  const [tagModalRunId, setTagModalRunId] = useState<string | null>(null)
  const [tagModalCurrentTags, setTagModalCurrentTags] = useState<string[]>([])

  const handleTagsUpdate = useCallback(async (runId: string, newTags: string[]) => {
    try {
      await updateRunTags(runId, newTags)
      setRuns(prev => prev.map(r =>
        r.run_id === runId ? { ...r, tags: newTags } : r
      ))
      message.success(t('experiments.tags_updated') || 'Tags updated')
    } catch (error) {
      logger.error('Failed to update tags:', error)
      message.error(t('experiments.tags_update_failed') || 'Failed to update tags')
    }
  }, [t, setRuns])

  const handleRemoveTag = useCallback((runId: string, tagToRemove: string, currentTags: string[]) => {
    const newTags = currentTags.filter(t => t !== tagToRemove)
    handleTagsUpdate(runId, newTags)
  }, [handleTagsUpdate])

  const handleOpenTagModal = useCallback((runId: string, currentTags: string[]) => {
    setTagModalRunId(runId)
    setTagModalCurrentTags(currentTags)
    setTagModalOpen(true)
  }, [])

  const handleAddTagFromModal = useCallback((tag: string) => {
    if (!tagModalRunId) return
    const newTags = [...tagModalCurrentTags, tag]
    handleTagsUpdate(tagModalRunId, newTags)
    setTagModalOpen(false)
    setTagModalRunId(null)
    setTagModalCurrentTags([])
  }, [tagModalRunId, tagModalCurrentTags, handleTagsUpdate])

  const handleCloseTagModal = useCallback(() => {
    setTagModalOpen(false)
    setTagModalRunId(null)
    setTagModalCurrentTags([])
  }, [])

  const allTagsFromRuns = useMemo(() => {
    return runs.flatMap(r => r.tags || [])
  }, [runs])

  return {
    editingRunId, editingAlias, setEditingAlias, aliasUpdateLoading,
    handleAliasEdit, handleAliasSave, handleAliasCancel,
    tagModalOpen, tagModalCurrentTags, allTagsFromRuns,
    handleTagsUpdate, handleRemoveTag, handleOpenTagModal,
    handleAddTagFromModal, handleCloseTagModal,
  }
}
