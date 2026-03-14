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
  listLocalStorageCandidates,
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

// ── Additional endpoint coverage ──

import {
  getRunAssets,
  getMetrics,
  getStepMetrics,
  getProgress,
  getGpuTelemetry,
  getGpuTelemetryHistory,
  getGpuTelemetryConfig,
  setGpuTelemetryConfig,
  getSystemMonitor,
  listProjects,
  listNames,
  listRunsByName,
  getConfig,
  setUserRootDir,
  getSavedSSHConnections,
  saveSSHConnection,
  deleteSSHConnection,
  getSSHConnectionDetails,
  importArchive,
  softDeleteRuns,
  listDeletedRuns,
  restoreRuns,
  emptyRecycleBin,
  moveRuns,
  checkAllStatus,
  softDeleteByPath,
  createPath,
  listPaths,
  getStorageStats,
  getRunAssetRefs,
  permanentDeleteRun,
  permanentDeleteRunsBatch,
  downloadRunAssetUrl,
  unifiedConnect,
  unifiedDisconnect,
  unifiedStatus,
  unifiedConfigureMode,
  unifiedDeactivateMode,
  unifiedListdir,
  sshConnect,
  sshSessions,
  sshClose,
  sshListdir,
  sshMirrorStart,
  sshMirrorStop,
  sshMirrorList,
} from '../../api'

describe('Run detail endpoints', () => {
  it('getRunAssets returns assets', async () => {
    const data = await getRunAssets('r1')
    expect(data.assets).toBeDefined()
  })

  it('getMetrics returns metrics', async () => {
    const data = await getMetrics('r1')
    expect(data.metrics).toBeDefined()
  })

  it('getMetrics with downsample', async () => {
    server.use(
      http.get('/api/runs/:id/metrics', ({ request }) => {
        const url = new URL(request.url)
        return HttpResponse.json({ downsample: url.searchParams.get('downsample') })
      }),
    )
    const data = await getMetrics('r1', 100)
    expect(data.downsample).toBe('100')
  })

  it('getStepMetrics returns metrics', async () => {
    const data = await getStepMetrics('r1')
    expect(data.metrics).toBeDefined()
  })

  it('getStepMetrics with downsample', async () => {
    server.use(
      http.get('/api/runs/:id/metrics_step', ({ request }) => {
        const url = new URL(request.url)
        return HttpResponse.json({ ds: url.searchParams.get('downsample') })
      }),
    )
    const data = await getStepMetrics('r1', 50)
    expect(data.ds).toBe('50')
  })

  it('getProgress returns progress', async () => {
    const data = await getProgress('r1')
    expect(data).toBeDefined()
  })

  it('downloadRunAssetUrl constructs correct URL', () => {
    const result = downloadRunAssetUrl('r1', '/path/to/file.txt')
    expect(result).toContain('/runs/r1/assets/download')
    expect(result).toContain('path=')
  })

  it('downloadRunAssetUrl includes filename when provided', () => {
    const result = downloadRunAssetUrl('r1', '/path/file.txt', 'custom.txt')
    expect(result).toContain('filename=custom.txt')
  })
})

describe('GPU endpoints', () => {
  it('getGpuTelemetry', async () => {
    const data = await getGpuTelemetry()
    expect(data).toBeDefined()
  })

  it('getGpuTelemetryHistory', async () => {
    const data = await getGpuTelemetryHistory()
    expect(data.available).toBe(false)
  })

  it('getGpuTelemetryConfig', async () => {
    const data = await getGpuTelemetryConfig()
    expect(data.enabled).toBe(false)
  })

  it('setGpuTelemetryConfig', async () => {
    const data = await setGpuTelemetryConfig({ enabled: true })
    expect(data.ok).toBe(true)
  })

  it('getSystemMonitor', async () => {
    const data = await getSystemMonitor()
    expect(data).toBeDefined()
  })
})

describe('Recycle bin endpoints', () => {
  it('softDeleteRuns', async () => {
    const data = await softDeleteRuns(['r1'])
    expect(data.deleted_count).toBe(1)
  })

  it('listDeletedRuns', async () => {
    const data = await listDeletedRuns()
    expect(data.deleted_runs).toEqual([])
  })

  it('restoreRuns', async () => {
    const data = await restoreRuns(['r1'])
    expect(data.restored_count).toBe(0)
  })

  it('emptyRecycleBin', async () => {
    const data = await emptyRecycleBin()
    expect(data.permanently_deleted).toBe(0)
  })
})

describe('Permanent delete endpoints', () => {
  it('getRunAssetRefs', async () => {
    const data = await getRunAssetRefs('r1')
    expect(data.orphaned_count).toBe(0)
  })

  it('permanentDeleteRun', async () => {
    const data = await permanentDeleteRun('r1')
    expect(data.success).toBe(true)
  })

  it('permanentDeleteRun with dryRun', async () => {
    server.use(
      http.delete('/api/runs/:id/permanent', ({ request }) => {
        const url = new URL(request.url)
        return HttpResponse.json({ success: true, dry_run: url.searchParams.get('dry_run') })
      }),
    )
    const data = await permanentDeleteRun('r1', true)
    expect(data.dry_run).toBe('true')
  })

  it('permanentDeleteRunsBatch', async () => {
    const data = await permanentDeleteRunsBatch(['r1', 'r2'])
    expect(data.deleted_count).toBe(0)
  })
})

describe('Move & status endpoints', () => {
  it('moveRuns', async () => {
    const data = await moveRuns(['r1'], 'new/path')
    expect(data.ok).toBe(true)
  })

  it('checkAllStatus', async () => {
    const data = await checkAllStatus()
    expect(data.message).toBe('ok')
  })
})

describe('Path endpoints', () => {
  it('softDeleteByPath', async () => {
    const data = await softDeleteByPath('proj/exp')
    expect(data.deleted_count).toBe(0)
  })

  it('createPath', async () => {
    const data = await createPath('new/path')
    expect(data.ok).toBe(true)
  })

  it('listPaths with stats', async () => {
    const data = await listPaths(true)
    expect(data).toBeDefined()
  })

  it('listPaths without stats', async () => {
    server.use(
      http.get('/api/paths', ({ request }) => {
        const url = new URL(request.url)
        return HttpResponse.json({ include_stats: url.searchParams.get('include_stats') })
      }),
    )
    const data = await listPaths(false)
    expect(data.include_stats).toBeNull()
  })
})

describe('Project hierarchy endpoints', () => {
  it('listProjects', async () => {
    const data = await listProjects()
    expect(data.projects).toEqual([])
  })

  it('listNames', async () => {
    server.use(
      http.get('/api/projects/:project/names', () =>
        HttpResponse.json({ names: ['exp1'] }),
      ),
    )
    const data = await listNames('projA')
    expect(data.names).toEqual(['exp1'])
  })

  it('listRunsByName', async () => {
    server.use(
      http.get('/api/projects/:project/names/:name/runs', () =>
        HttpResponse.json({ runs: [] }),
      ),
    )
    const data = await listRunsByName('projA', 'exp1')
    expect(data.runs).toEqual([])
  })
})

describe('Config & SSH connection endpoints', () => {
  it('getConfig', async () => {
    const data = await getConfig()
    expect(data.user_root_dir).toBe('/tmp')
  })

  it('setUserRootDir', async () => {
    const data = await setUserRootDir('/new/path')
    expect(data.ok).toBe(true)
  })

  it('listLocalStorageCandidates', async () => {
    server.use(
      http.get('/api/config/storage-candidates', () =>
        HttpResponse.json({
          candidates: [
            {
              path: '/tmp/runicorn_data',
              run_count: 2,
              has_archive: true,
              has_index: false,
            },
          ],
        }),
      ),
    )
    const data = await listLocalStorageCandidates('/tmp', 2)
    expect(data).toHaveLength(1)
    expect(data[0].path).toBe('/tmp/runicorn_data')
    expect(data[0].runCount).toBe(2)
  })

  it('getSavedSSHConnections', async () => {
    const data = await getSavedSSHConnections()
    expect(data.connections).toEqual([])
  })

  it('saveSSHConnection', async () => {
    server.use(
      http.post('/api/config/ssh_connections', () =>
        HttpResponse.json({ ok: true, message: 'saved' }),
      ),
    )
    const data = await saveSSHConnection({
      host: 'h', port: 22, username: 'u', auth_method: 'password', remember_password: false,
    })
    expect(data.ok).toBe(true)
  })

  it('deleteSSHConnection', async () => {
    server.use(
      http.delete('/api/config/ssh_connections/:key', () =>
        HttpResponse.json({ ok: true, message: 'deleted' }),
      ),
    )
    const data = await deleteSSHConnection('key1')
    expect(data.ok).toBe(true)
  })

  it('getSSHConnectionDetails', async () => {
    server.use(
      http.get('/api/config/ssh_connections/:key/details', () =>
        HttpResponse.json({ ok: true, connection: {} }),
      ),
    )
    const data = await getSSHConnectionDetails('key1')
    expect(data.ok).toBe(true)
  })
})

describe('Storage stats', () => {
  it('getStorageStats', async () => {
    const data = await getStorageStats()
    expect(data.storage_root).toBe('')
  })
})

describe('importArchive (legacy)', () => {
  it('sends file via FormData', async () => {
    const file = new File(['data'], 'test.zip', { type: 'application/zip' })
    const data = await importArchive(file)
    expect(data.ok).toBe(true)
  })
})

describe('Unified SSH helpers', () => {
  beforeEach(() => {
    server.use(
      http.post('/api/unified/connect', () => HttpResponse.json({ ok: true, session_id: 's1' })),
      http.post('/api/unified/disconnect', () => HttpResponse.json({ ok: true })),
      http.get('/api/unified/status', () => HttpResponse.json({ connected: false })),
      http.post('/api/unified/configure_mode', () => HttpResponse.json({ ok: true })),
      http.post('/api/unified/deactivate_mode', () => HttpResponse.json({ ok: true })),
      http.get('/api/unified/listdir', () => HttpResponse.json({ items: [], current_path: '/', ok: true })),
    )
  })

  it('unifiedConnect', async () => {
    const data = await unifiedConnect({ host: 'h', username: 'u' })
    expect(data.ok).toBe(true)
  })

  it('unifiedDisconnect', async () => {
    const data = await unifiedDisconnect()
    expect(data.ok).toBe(true)
  })

  it('unifiedStatus', async () => {
    const data = await unifiedStatus()
    expect(data.connected).toBe(false)
  })

  it('unifiedConfigureMode', async () => {
    const data = await unifiedConfigureMode({ mode: 'smart' })
    expect(data.ok).toBe(true)
  })

  it('unifiedDeactivateMode', async () => {
    const data = await unifiedDeactivateMode('mirror')
    expect(data.ok).toBe(true)
  })

  it('unifiedListdir', async () => {
    const data = await unifiedListdir('/home')
    expect(data.ok).toBe(true)
  })

  it('unifiedListdir without path', async () => {
    const data = await unifiedListdir()
    expect(data.ok).toBe(true)
  })
})

describe('SSH live sync helpers', () => {
  beforeEach(() => {
    server.use(
      http.post('/api/ssh/connect', () => HttpResponse.json({ ok: true, session_id: 's1' })),
      http.get('/api/ssh/sessions', () => HttpResponse.json({ sessions: [] })),
      http.post('/api/ssh/close', () => HttpResponse.json({ ok: true })),
      http.get('/api/ssh/listdir', () => HttpResponse.json({ items: [] })),
      http.post('/api/ssh/mirror/start', () => HttpResponse.json({ ok: true, task: {} })),
      http.post('/api/ssh/mirror/stop', () => HttpResponse.json({ ok: true })),
      http.get('/api/ssh/mirror/list', () => HttpResponse.json({ mirrors: [], storage: '/tmp' })),
    )
  })

  it('sshConnect', async () => {
    const data = await sshConnect({ host: 'h', username: 'u' })
    expect(data.ok).toBe(true)
  })

  it('sshSessions', async () => {
    const data = await sshSessions()
    expect(data.sessions).toEqual([])
  })

  it('sshClose', async () => {
    const data = await sshClose('s1')
    expect(data.ok).toBe(true)
  })

  it('sshListdir', async () => {
    const data = await sshListdir('s1', '/home')
    expect(data.items).toEqual([])
  })

  it('sshMirrorStart', async () => {
    const data = await sshMirrorStart({ session_id: 's1', remote_root: '/data' })
    expect(data.ok).toBe(true)
  })

  it('sshMirrorStop', async () => {
    const data = await sshMirrorStop('t1')
    expect(data.ok).toBe(true)
  })

  it('sshMirrorList', async () => {
    const data = await sshMirrorList()
    expect(data.mirrors).toEqual([])
  })
})
