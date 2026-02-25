import { describe, it, expect, vi, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../__mocks__/server'
import {
  listRuns,
  getRunDetail,
  health,
  exportRunsZip,
  previewImport,
  confirmImport,
  updateRunAlias,
  updateRunTags,
  getColumnWidths,
  saveColumnWidths,
} from '../../api'

describe('apiFetch — core behavior', () => {
  it('GET request returns parsed JSON', async () => {
    server.use(
      http.get('/api/runs', () =>
        HttpResponse.json({ runs: [{ run_id: 'r1' }] }),
      ),
    )
    const data = await listRuns()
    expect(data.runs).toHaveLength(1)
    expect(data.runs[0].run_id).toBe('r1')
  })

  it('GET with path param works', async () => {
    server.use(
      http.get('/api/runs/:id', ({ params }) =>
        HttpResponse.json({ run_id: params.id, status: 'running' }),
      ),
    )
    const data = await getRunDetail('abc')
    expect(data.run_id).toBe('abc')
    expect(data.status).toBe('running')
  })

  it('throws on 4xx response', async () => {
    server.use(
      http.get('/api/runs', () =>
        new HttpResponse('Not Found', { status: 404 }),
      ),
    )
    await expect(listRuns()).rejects.toThrow('Not Found')
  })

  it('throws on 5xx response', async () => {
    server.use(
      http.get('/api/runs', () =>
        new HttpResponse('Internal Server Error', { status: 500 }),
      ),
    )
    await expect(listRuns()).rejects.toThrow('Internal Server Error')
  })
})

describe('health()', () => {
  it('returns JSON on success', async () => {
    const data = await health()
    expect(data.status).toBe('ok')
  })

  it('throws on timeout (abort signal)', async () => {
    server.use(
      http.get('/api/health', async () => {
        await new Promise((r) => setTimeout(r, 5000))
        return HttpResponse.json({})
      }),
    )
    await expect(health()).rejects.toThrow()
  })
})

describe('POST / PATCH endpoints', () => {
  it('updateRunAlias sends PATCH', async () => {
    server.use(
      http.patch('/api/runs/:id', async ({ request }) => {
        const body = await request.json() as any
        return HttpResponse.json({ ok: true, alias: body.alias })
      }),
    )
    const data = await updateRunAlias('r1', 'my-alias')
    expect(data.ok).toBe(true)
    expect(data.alias).toBe('my-alias')
  })

  it('updateRunTags sends PATCH with tags', async () => {
    server.use(
      http.patch('/api/runs/:id', async ({ request }) => {
        const body = await request.json() as any
        return HttpResponse.json({ ok: true, tags: body.tags })
      }),
    )
    const data = await updateRunTags('r1', ['a', 'b'])
    expect(data.tags).toEqual(['a', 'b'])
  })
})

describe('exportRunsZip', () => {
  beforeEach(() => {
    // Mock DOM methods used by exportRunsZip
    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click: vi.fn(),
    } as any)
    vi.spyOn(document.body, 'appendChild').mockImplementation((node) => node)
    vi.spyOn(document.body, 'removeChild').mockImplementation((node) => node)
  })

  it('triggers blob download', async () => {
    await expect(exportRunsZip(['r1', 'r2'])).resolves.toBeUndefined()
  })
})

describe('previewImport', () => {
  it('sends FormData with file', async () => {
    const file = new File(['content'], 'archive.zip', { type: 'application/zip' })
    const data = await previewImport(file)
    expect(data.ok).toBe(true)
    expect(data.token).toBe('tok')
  })
})

describe('confirmImport', () => {
  it('sends correct mode', async () => {
    server.use(
      http.post('/api/import/archive', async ({ request }) => {
        const fd = await request.formData()
        return HttpResponse.json({
          ok: true,
          mode: fd.get('mode'),
          imported_files: 0,
          new_run_dirs: [],
          new_run_ids: [],
          skipped_run_ids: [],
          skipped_count: 0,
          storage: '',
          isolate_base: null,
        })
      }),
    )
    const data = await confirmImport('tok', 'isolate')
    expect(data.mode).toBe('isolate')
  })
})

describe('column width config', () => {
  it('getColumnWidths returns null on error', async () => {
    server.use(
      http.get('/api/config/column-widths', () =>
        new HttpResponse('fail', { status: 500 }),
      ),
    )
    const data = await getColumnWidths('table1', 'lg')
    expect(data).toBeNull()
  })

  it('saveColumnWidths sends POST', async () => {
    await expect(
      saveColumnWidths({ table: 't', size: 'lg', widths: { a: 100 }, window_width: 1920, window_height: 1080 }),
    ).resolves.toBeUndefined()
  })
})
