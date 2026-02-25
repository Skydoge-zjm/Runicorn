import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useExperimentFilters } from './useExperimentFilters'
import type { RunData } from './useExperimentData'

const mockRuns: RunData[] = [
  { run_id: 'r1', path: 'projA/exp1', alias: 'baseline', tags: ['v1', 'prod'], status: 'running', created: '2024-01-01', summary: {} },
  { run_id: 'r2', path: 'projA/exp1', alias: null, tags: ['v2'], status: 'finished', created: '2024-01-02', summary: {} },
  { run_id: 'r3', path: 'projB/exp2', alias: 'ablation', tags: [], status: 'failed', created: '2024-01-03', summary: {} },
]

beforeEach(() => {
  localStorage.clear()
})

describe('useExperimentFilters', () => {
  // ── filteredRuns ──
  it('returns all runs with no filters', () => {
    const { result } = renderHook(() => useExperimentFilters(mockRuns))
    expect(result.current.filteredRuns).toHaveLength(3)
  })

  it('filters by searchText matching run_id', () => {
    const { result } = renderHook(() => useExperimentFilters(mockRuns))
    act(() => result.current.setSearchText('r1'))
    expect(result.current.filteredRuns).toHaveLength(1)
    expect(result.current.filteredRuns[0].run_id).toBe('r1')
  })

  it('filters by searchText matching alias', () => {
    const { result } = renderHook(() => useExperimentFilters(mockRuns))
    act(() => result.current.setSearchText('baseline'))
    expect(result.current.filteredRuns).toHaveLength(1)
    expect(result.current.filteredRuns[0].run_id).toBe('r1')
  })

  it('filters by searchText matching tags', () => {
    const { result } = renderHook(() => useExperimentFilters(mockRuns))
    act(() => result.current.setSearchText('v2'))
    expect(result.current.filteredRuns).toHaveLength(1)
    expect(result.current.filteredRuns[0].run_id).toBe('r2')
  })

  it('filters by projectFilter', () => {
    const { result } = renderHook(() => useExperimentFilters(mockRuns))
    act(() => result.current.setProjectFilter('projB'))
    expect(result.current.filteredRuns).toHaveLength(1)
    expect(result.current.filteredRuns[0].run_id).toBe('r3')
  })

  it('filters by statusFilter', () => {
    const { result } = renderHook(() => useExperimentFilters(mockRuns))
    act(() => result.current.setStatusFilter('running'))
    expect(result.current.filteredRuns).toHaveLength(1)
    expect(result.current.filteredRuns[0].run_id).toBe('r1')
  })

  it('filters by selectedTreePath (exact and child paths)', () => {
    const { result } = renderHook(() => useExperimentFilters(mockRuns))
    act(() => result.current.setSelectedTreePath('projA'))
    // r1, r2 have path starting with 'projA/'
    expect(result.current.filteredRuns).toHaveLength(2)
  })

  it('combines multiple filters with AND logic', () => {
    const { result } = renderHook(() => useExperimentFilters(mockRuns))
    act(() => {
      result.current.setProjectFilter('projA')
      result.current.setStatusFilter('running')
    })
    expect(result.current.filteredRuns).toHaveLength(1)
    expect(result.current.filteredRuns[0].run_id).toBe('r1')
  })

  // ── persistence ──
  it('persists pageSize to localStorage', () => {
    const { result } = renderHook(() => useExperimentFilters(mockRuns))
    act(() => result.current.setPageSize(25))
    const saved = JSON.parse(localStorage.getItem('experiment_preferences') || '{}')
    expect(saved.pageSize).toBe(25)
  })

  it('restores pageSize from localStorage', () => {
    localStorage.setItem('experiment_preferences', JSON.stringify({ pageSize: 50 }))
    const { result } = renderHook(() => useExperimentFilters(mockRuns))
    expect(result.current.pageSize).toBe(50)
  })

  it('persists treePanelCollapsed to localStorage', () => {
    const { result } = renderHook(() => useExperimentFilters(mockRuns))
    act(() => result.current.setTreePanelCollapsed(true))
    expect(localStorage.getItem('tree_panel_collapsed')).toBe('true')
  })
})
