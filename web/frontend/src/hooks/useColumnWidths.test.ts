import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../__mocks__/server'
import { useColumnWidths } from './useColumnWidths'

const defaults = { name: 200, status: 100, created: 150 }

describe('useColumnWidths', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('initializes with defaultWidths', () => {
    const { result } = renderHook(() => useColumnWidths('test-table', defaults))
    expect(result.current.columnWidths).toEqual(defaults)
  })

  it('loadPreferences merges API widths over defaults', async () => {
    server.use(
      http.get('/api/config/column-widths', () =>
        HttpResponse.json({ widths: { name: 300 } }),
      ),
    )

    const { result } = renderHook(() => useColumnWidths('test-table', defaults))

    await waitFor(() => {
      expect(result.current.columnWidths.name).toBe(300)
    })
    // Other defaults preserved
    expect(result.current.columnWidths.status).toBe(100)
  })

  it('setColumnWidth updates a single column', () => {
    const { result } = renderHook(() => useColumnWidths('test-table', defaults))
    act(() => result.current.setColumnWidth('name', 250))
    expect(result.current.columnWidths.name).toBe(250)
  })

  it('resetWidths restores defaults', async () => {
    server.use(
      http.get('/api/config/column-widths', () =>
        HttpResponse.json({ widths: { name: 300 } }),
      ),
    )

    const { result } = renderHook(() => useColumnWidths('test-table', defaults))
    await waitFor(() => expect(result.current.columnWidths.name).toBe(300))

    act(() => result.current.resetWidths())
    expect(result.current.columnWidths).toEqual(defaults)
  })
})
