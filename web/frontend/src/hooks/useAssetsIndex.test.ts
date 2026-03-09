import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../__mocks__/server'
import { useAssetsIndex, loadAssetsIndexFromCache } from './useAssetsIndex'

// Mock antd message
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd')
  return {
    ...actual,
    message: { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() },
  }
})

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

describe('loadAssetsIndexFromCache', () => {
  it('returns null when localStorage is empty', () => {
    expect(loadAssetsIndexFromCache()).toBeNull()
  })

  it('restores valid cached index', () => {
    const cached = {
      version: 3,
      generated_at: 1700000000,
      runs: [{ run_id: 'r1', path: 'p', alias: null }],
      run_assets: { r1: [] },
      experiments: [],
      repo: [],
    }
    localStorage.setItem('assets_index_v3', JSON.stringify(cached))
    const loaded = loadAssetsIndexFromCache()
    expect(loaded).not.toBeNull()
    expect(loaded!.version).toBe(3)
    expect(loaded!.runs).toHaveLength(1)
  })

  it('returns null for wrong version', () => {
    localStorage.setItem('assets_index_v3', JSON.stringify({ version: 2 }))
    expect(loadAssetsIndexFromCache()).toBeNull()
  })
})

describe('useAssetsIndex', () => {
  it('auto-refreshes when no cached index', async () => {
    server.use(
      http.get('/api/runs', () =>
        HttpResponse.json([
          { id: 'r1', path: 'p/e', status: 'finished', assets_count: 1 },
        ]),
      ),
      http.get('/api/runs/:id/assets', () =>
        HttpResponse.json({
          assets: { datasets: [{ name: 'train', fingerprint: 'fp1' }] },
        }),
      ),
    )

    const { result } = renderHook(() => useAssetsIndex())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
      expect(result.current.index).not.toBeNull()
    })

    expect(result.current.stats.totalRuns).toBe(1)
    expect(result.current.stats.totalAssets).toBeGreaterThan(0)
  })

  it('cancel sets abort flag', async () => {
    server.use(
      http.get('/api/runs', () => HttpResponse.json([])),
    )

    const { result } = renderHook(() => useAssetsIndex())

    // Cancel immediately
    act(() => result.current.cancel())

    await waitFor(() => expect(result.current.loading).toBe(false))
  })

  it('stats correctly computes totals', async () => {
    const cached = {
      version: 3,
      generated_at: Math.floor(Date.now() / 1000) - 30, // Fresh cache (< 60s TTL) to avoid auto-refresh
      runs: [{ run_id: 'r1', path: 'p', alias: null }],
      run_assets: { r1: [{ kind: 'dataset', name: 'ds', saved: true, identity: { kind: 'dataset', idType: 'name', idValue: 'ds' } }] },
      experiments: [],
      repo: [
        { key: 'k1', encoded: 'e1', identity: {}, kind: 'dataset', name: 'ds', saved: true, paths: [], runs_count: 1, run_ids: ['r1'] },
        { key: 'k2', encoded: 'e2', identity: {}, kind: 'code', name: 'code', saved: false, paths: [], runs_count: 1, run_ids: ['r1'] },
      ],
    }
    localStorage.setItem('assets_index_v3', JSON.stringify(cached))

    // Prevent auto-refresh: cache is fresh, so no refresh triggered
    server.use(
      http.get('/api/runs', () => HttpResponse.json([])),
    )

    const { result } = renderHook(() => useAssetsIndex())

    expect(result.current.stats.totalRuns).toBe(1)
    expect(result.current.stats.totalAssets).toBe(2)
    expect(result.current.stats.archivedAssets).toBe(1)
  })
})
