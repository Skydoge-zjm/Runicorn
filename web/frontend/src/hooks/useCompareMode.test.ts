import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../__mocks__/server'
import { createWrapper } from '../__tests__/helpers'
import { useCompareMode } from './useCompareMode'
import type { RunData } from './useExperimentData'

// Mock antd message
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd')
  return {
    ...actual,
    message: { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() },
  }
})

import { message } from 'antd'

const mockRuns: RunData[] = [
  { run_id: 'r1', path: 'p/e', alias: 'a1', tags: [], status: 'finished', created: '', summary: {} },
  { run_id: 'r2', path: 'p/e', alias: 'a2', tags: [], status: 'running', created: '', summary: {} },
  { run_id: 'r3', path: 'p/e', alias: null, tags: [], status: 'finished', created: '', summary: {} },
]

describe('useCompareMode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    server.use(
      http.get('/api/runs/:id/metrics_step', () =>
        HttpResponse.json({ metrics: { loss: [[1, 0.5], [2, 0.3]] } }),
      ),
    )
  })

  it('initial state has compareMode=false', () => {
    const { result } = renderHook(() => useCompareMode(mockRuns, []), {
      wrapper: createWrapper(),
    })
    expect(result.current.compareMode).toBe(false)
  })

  it('handleCompare warns when less than 2 selected', async () => {
    const { result } = renderHook(() => useCompareMode(mockRuns, ['r1']), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.handleCompare()
    })

    expect(message.warning).toHaveBeenCalledWith('experiments.select_multiple')
  })

  it('handleCompare fetches metrics and enters compare mode', async () => {
    const { result } = renderHook(() => useCompareMode(mockRuns, ['r1', 'r2']), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.handleCompare()
    })

    await waitFor(() => {
      expect(result.current.compareRunInfos).toHaveLength(2)
      expect(result.current.compareLoading).toBe(false)
    })
  })

  it('toggleRunVisibility toggles a run', async () => {
    const { result } = renderHook(() => useCompareMode(mockRuns, ['r1', 'r2']), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.handleCompare()
    })

    await waitFor(() => expect(result.current.visibleRunIds.has('r1')).toBe(true))

    act(() => result.current.toggleRunVisibility('r1'))
    expect(result.current.visibleRunIds.has('r1')).toBe(false)

    act(() => result.current.toggleRunVisibility('r1'))
    expect(result.current.visibleRunIds.has('r1')).toBe(true)
  })

  it('handleExitCompare clears all compare state', async () => {
    const { result } = renderHook(() => useCompareMode(mockRuns, ['r1', 'r2']), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.handleCompare()
    })

    await waitFor(() => expect(result.current.compareRunInfos.length).toBeGreaterThan(0))

    act(() => result.current.handleExitCompare())
    expect(result.current.compareRunInfos).toHaveLength(0)
    expect(result.current.compareMetrics.size).toBe(0)
  })

  it('restores compare mode from URL params', async () => {
    const { result } = renderHook(() => useCompareMode(mockRuns, []), {
      wrapper: createWrapper({ initialEntries: ['/?compare=r1,r2'] }),
    })

    await waitFor(() => {
      expect(result.current.compareRunInfos).toHaveLength(2)
    })
  })

  // ── Additional branch coverage ──

  it('handleCompare uses alias for label, falls back to path segment then run_id suffix', async () => {
    const { result } = renderHook(() => useCompareMode(mockRuns, ['r1', 'r3']), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.handleCompare()
    })

    await waitFor(() => expect(result.current.compareRunLabels.size).toBe(2))
    // r1 has alias 'a1'
    expect(result.current.compareRunLabels.get('r1')).toBe('a1')
    // r3 has no alias, path 'p/e' → last segment 'e'
    expect(result.current.compareRunLabels.get('r3')).toBe('e')
  })

  it('handleCompare handles metrics fetch failure gracefully', async () => {
    server.use(
      http.get('/api/runs/:id/metrics_step', () =>
        new HttpResponse('fail', { status: 500 }),
      ),
    )

    const { result } = renderHook(() => useCompareMode(mockRuns, ['r1', 'r2']), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.handleCompare()
    })

    await waitFor(() => expect(result.current.compareLoading).toBe(false))
    // Metrics map should still exist but may be empty due to per-run catch
    expect(result.current.compareMetrics).toBeDefined()
  })

  it('handleAddRuns shows info message', async () => {
    const { result } = renderHook(() => useCompareMode(mockRuns, []), {
      wrapper: createWrapper(),
    })

    act(() => result.current.handleAddRuns())
    expect(message.info).toHaveBeenCalledWith('experiments.add_runs_coming_soon')
  })

  it('URL restore skips when fewer than 2 matching runs found', async () => {
    // URL has r1,r_nonexistent → only r1 matches → selectedRuns.length < 2 → skip
    const { result } = renderHook(() => useCompareMode(mockRuns, []), {
      wrapper: createWrapper({ initialEntries: ['/?compare=r1,r_nonexistent'] }),
    })

    // Wait a tick for useEffect to run
    await new Promise((r) => setTimeout(r, 50))
    expect(result.current.compareRunInfos).toHaveLength(0)
  })

  it('compareMode is true when URL has 2+ IDs and false otherwise', () => {
    const { result: r1 } = renderHook(() => useCompareMode([], []), {
      wrapper: createWrapper({ initialEntries: ['/?compare=a,b'] }),
    })
    expect(r1.current.compareMode).toBe(true)

    const { result: r2 } = renderHook(() => useCompareMode([], []), {
      wrapper: createWrapper({ initialEntries: ['/?compare=a'] }),
    })
    expect(r2.current.compareMode).toBe(false)
  })
})
