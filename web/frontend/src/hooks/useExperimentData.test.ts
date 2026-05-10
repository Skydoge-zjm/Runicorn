import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../__mocks__/server'
import { createWrapper } from '../__tests__/helpers'
import { useExperimentData } from './useExperimentData'

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

  // ── Additional branch coverage ──

  it('handleBatchDeleteByPath shows error on API failure', async () => {
    const { message } = await import('antd')

    server.use(
      http.get('/api/runs', () => HttpResponse.json({ runs: [] })),
      http.post('/api/paths/soft-delete', () =>
        new HttpResponse('Server Error', { status: 500 }),
      ),
    )

    const { result } = renderHook(() => useExperimentData('test'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.loading).toBe(false))
    await result.current.handleBatchDeleteByPath('proj/exp')

    expect(message.error).toHaveBeenCalled()
  })

  it('handleBatchExportByPath creates download link and shows success', async () => {
    const { message } = await import('antd')

    const clickSpy = vi.fn()
    const origCreate = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tag: string, options?: any) => {
      if (tag === 'a') {
        return { href: '', download: '', click: clickSpy } as any
      }
      return origCreate(tag, options)
    })
    vi.spyOn(document.body, 'appendChild').mockImplementation((n) => n)
    vi.spyOn(document.body, 'removeChild').mockImplementation((n) => n)

    server.use(
      http.get('/api/runs', () => HttpResponse.json({ runs: [] })),
    )

    const { result } = renderHook(() => useExperimentData('test'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.loading).toBe(false))
    await result.current.handleBatchExportByPath('proj/exp')

    expect(clickSpy).toHaveBeenCalled()
    expect(message.success).toHaveBeenCalled()

    vi.restoreAllMocks()
  })

  it('mapRuns handles Array input (no .runs wrapper)', async () => {
    server.use(
      http.get('/api/runs', () =>
        HttpResponse.json([
          { id: 'r1', path: 'p', status: 'finished' },
        ]),
      ),
    )

    const { result } = renderHook(() => useExperimentData('test'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.runs).toHaveLength(1))
    expect(result.current.runs[0].run_id).toBe('r1')
  })

  it('mapRuns uses run_id field when id is missing', async () => {
    server.use(
      http.get('/api/runs', () =>
        HttpResponse.json({ runs: [{ run_id: 'rx', path: 'p', status: 'ok' }] }),
      ),
    )

    const { result } = renderHook(() => useExperimentData('test'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.runs).toHaveLength(1))
    expect(result.current.runs[0].run_id).toBe('rx')
  })

  it('mapRuns defaults missing fields', async () => {
    server.use(
      http.get('/api/runs', () =>
        HttpResponse.json({ runs: [{ id: 'r1' }] }),
      ),
    )

    const { result } = renderHook(() => useExperimentData('test'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.runs).toHaveLength(1))
    const run = result.current.runs[0]
    expect(run.path).toBe('default')
    expect(run.alias).toBeNull()
    expect(run.tags).toEqual([])
    expect(run.status).toBe('unknown')
    expect(run.assets_count).toBe(0)
  })

  it('projects are extracted from run paths', async () => {
    server.use(
      http.get('/api/runs', () =>
        HttpResponse.json({
          runs: [
            { id: 'r1', path: 'projA/exp1', status: 'finished' },
            { id: 'r2', path: 'projB/exp2', status: 'running' },
            { id: 'r3', path: 'projA/exp3', status: 'finished' },
          ],
        }),
      ),
    )

    const { result } = renderHook(() => useExperimentData('test'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.runs).toHaveLength(3))
    expect(result.current.projects).toContain('projA')
    expect(result.current.projects).toContain('projB')
    expect(result.current.projects).toHaveLength(2)
  })
})
