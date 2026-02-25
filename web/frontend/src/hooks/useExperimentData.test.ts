import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../__mocks__/server'
import { createWrapper } from '../__tests__/helpers'
import { useExperimentData } from './useExperimentData'

// Mock antd message
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd')
  return {
    ...actual,
    message: { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() },
  }
})

describe('useExperimentData', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('initial loading returns mapped RunData[]', async () => {
    server.use(
      http.get('/api/runs', () =>
        HttpResponse.json({
          runs: [
            { id: 'r1', path: 'proj/exp', status: 'running', created_time: 1700000000, tags: ['a'] },
            { id: 'r2', path: 'proj/exp', status: 'finished', created_time: 1700000001 },
          ],
        }),
      ),
    )

    const { result } = renderHook(() => useExperimentData('test'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.runs).toHaveLength(2)
    })

    expect(result.current.runs[0].run_id).toBe('r1')
    expect(result.current.runs[0].tags).toEqual(['a'])
    expect(result.current.runs[1].tags).toEqual([])
  })

  it('computes stats correctly', async () => {
    server.use(
      http.get('/api/runs', () =>
        HttpResponse.json({
          runs: [
            { id: 'r1', path: 'p', status: 'running' },
            { id: 'r2', path: 'p', status: 'finished' },
            { id: 'r3', path: 'p', status: 'failed' },
            { id: 'r4', path: 'p', status: 'finished' },
          ],
        }),
      ),
    )

    const { result } = renderHook(() => useExperimentData('test'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.runs).toHaveLength(4))

    expect(result.current.stats).toEqual({
      total: 4,
      running: 1,
      finished: 2,
      failed: 1,
    })
  })

  it('fetchRuns invalidates queries', async () => {
    server.use(
      http.get('/api/runs', () => HttpResponse.json({ runs: [] })),
    )

    const { result } = renderHook(() => useExperimentData('test'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.loading).toBe(false))

    // Should not throw
    await result.current.fetchRuns()
  })

  it('handleBatchDeleteByPath with deleted_count > 0 shows success', async () => {
    const { message } = await import('antd')

    server.use(
      http.get('/api/runs', () => HttpResponse.json({ runs: [] })),
      http.post('/api/paths/soft-delete', () =>
        HttpResponse.json({ deleted_count: 3 }),
      ),
    )

    const { result } = renderHook(() => useExperimentData('test'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.loading).toBe(false))
    await result.current.handleBatchDeleteByPath('proj/exp')

    expect(message.success).toHaveBeenCalled()
  })

  it('handleBatchDeleteByPath with deleted_count=0 shows info', async () => {
    const { message } = await import('antd')

    server.use(
      http.get('/api/runs', () => HttpResponse.json({ runs: [] })),
      http.post('/api/paths/soft-delete', () =>
        HttpResponse.json({ deleted_count: 0 }),
      ),
    )

    const { result } = renderHook(() => useExperimentData('test'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.loading).toBe(false))
    await result.current.handleBatchDeleteByPath('proj/exp')

    expect(message.info).toHaveBeenCalled()
  })
})
