import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../__mocks__/server'
import { createWrapper } from '../__tests__/helpers'

// Mock react-i18next before importing the hook
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: vi.fn() },
  }),
}))

import { message } from 'antd'
import { useInlineEditing } from './useInlineEditing'
import type { RunData } from './useExperimentData'

const mockRuns: RunData[] = [
  { run_id: 'r1', path: 'p/e', alias: 'old-alias', tags: ['a', 'b'], status: 'finished', created: '', summary: {} },
  { run_id: 'r2', path: 'p/e', alias: null, tags: ['c'], status: 'running', created: '', summary: {} },
]

describe('useInlineEditing', () => {
  let setRuns: ReturnType<typeof vi.fn>

  beforeEach(() => {
    setRuns = vi.fn()
    vi.clearAllMocks()
  })

  it('handleAliasEdit sets editingRunId and editingAlias', () => {
    const { result } = renderHook(() => useInlineEditing(mockRuns, setRuns), {
      wrapper: createWrapper(),
    })
    act(() => result.current.handleAliasEdit('r1', 'old-alias'))
    expect(result.current.editingRunId).toBe('r1')
    expect(result.current.editingAlias).toBe('old-alias')
  })

  it('handleAliasSave calls API and optimistically updates runs', async () => {
    server.use(
      http.patch('/api/runs/:id', () =>
        HttpResponse.json({ ok: true, alias: 'new-alias' }),
      ),
    )

    const { result } = renderHook(() => useInlineEditing(mockRuns, setRuns), {
      wrapper: createWrapper(),
    })
    act(() => {
      result.current.handleAliasEdit('r1', 'old-alias')
      result.current.setEditingAlias('new-alias')
    })

    await act(async () => {
      await result.current.handleAliasSave('r1')
    })

    expect(setRuns).toHaveBeenCalled()
    expect(message.success).toHaveBeenCalledWith('experiments.alias_updated')
    expect(result.current.editingRunId).toBeNull()
  })

  it('handleAliasSave shows error on failure', async () => {
    server.use(
      http.patch('/api/runs/:id', () =>
        new HttpResponse('fail', { status: 500 }),
      ),
    )

    const { result } = renderHook(() => useInlineEditing(mockRuns, setRuns), {
      wrapper: createWrapper(),
    })
    act(() => {
      result.current.handleAliasEdit('r1', 'old')
      result.current.setEditingAlias('new')
    })

    await act(async () => {
      await result.current.handleAliasSave('r1')
    })

    expect(message.error).toHaveBeenCalledWith('experiments.alias_update_failed')
  })

  it('handleAliasCancel resets state', () => {
    const { result } = renderHook(() => useInlineEditing(mockRuns, setRuns), {
      wrapper: createWrapper(),
    })
    act(() => result.current.handleAliasEdit('r1', 'alias'))
    act(() => result.current.handleAliasCancel())
    expect(result.current.editingRunId).toBeNull()
    expect(result.current.editingAlias).toBe('')
  })

  it('handleRemoveTag removes the specified tag', async () => {
    const { result } = renderHook(() => useInlineEditing(mockRuns, setRuns), {
      wrapper: createWrapper(),
    })
    await act(async () => {
      result.current.handleRemoveTag('r1', 'a', ['a', 'b'])
    })
    // Should call updateRunTags with ['b']
    await waitFor(() => expect(setRuns).toHaveBeenCalled())
  })

  it('handleOpenTagModal / handleAddTagFromModal / handleCloseTagModal flow', async () => {
    const { result } = renderHook(() => useInlineEditing(mockRuns, setRuns), {
      wrapper: createWrapper(),
    })

    act(() => result.current.handleOpenTagModal('r1', ['a', 'b']))
    expect(result.current.tagModalOpen).toBe(true)

    await act(async () => {
      result.current.handleAddTagFromModal('c')
    })
    expect(result.current.tagModalOpen).toBe(false)
    await waitFor(() => expect(setRuns).toHaveBeenCalled())
  })

  it('allTagsFromRuns collects all tags from runs', () => {
    const { result } = renderHook(() => useInlineEditing(mockRuns, setRuns), {
      wrapper: createWrapper(),
    })
    expect(result.current.allTagsFromRuns).toEqual(['a', 'b', 'c'])
  })
})
