import { http, HttpResponse } from 'msw'

const BASE = '/api'

export const handlers = [
  // ── Health ──
  http.get(`${BASE}/health`, () =>
    HttpResponse.json({
      status: 'ok',
      version: '0.1.0',
      storage_backend: {
        mode: 'sqlite',
        label: 'SQLite-backed',
        available: true,
        backend_class: 'SQLiteStorageBackend',
      },
    }),
  ),

  // ── Runs ──
  http.get(`${BASE}/runs`, () =>
    HttpResponse.json({ runs: [] }),
  ),
  http.get(`${BASE}/runs/:id`, ({ params }) =>
    HttpResponse.json({ run_id: params.id, status: 'finished' }),
  ),
  http.get(`${BASE}/runs/:id/assets`, () =>
    HttpResponse.json({ assets: {} }),
  ),
  http.get(`${BASE}/runs/:id/metrics`, () =>
    HttpResponse.json({ metrics: {} }),
  ),
  http.get(`${BASE}/runs/:id/metrics_step`, () =>
    HttpResponse.json({ metrics: {} }),
  ),
  http.get(`${BASE}/runs/:id/images`, () =>
    HttpResponse.json([]),
  ),
  http.get(`${BASE}/runs/:id/progress`, () =>
    HttpResponse.json({ progress: null }),
  ),
  http.get(`${BASE}/runs/:id/assets/refs`, () =>
    HttpResponse.json({
      run_id: 'test',
      orphaned_assets: [],
      shared_assets: [],
      orphaned_count: 0,
      shared_count: 0,
    }),
  ),
  http.post(`${BASE}/runs/export`, () =>
    new HttpResponse(new Blob(['fake-zip']), {
      headers: { 'Content-Type': 'application/zip' },
    }),
  ),
  http.post(`${BASE}/runs/soft-delete`, () =>
    HttpResponse.json({ deleted_count: 1, results: {}, message: 'ok' }),
  ),
  http.patch(`${BASE}/runs/:id`, () =>
    HttpResponse.json({ ok: true }),
  ),
  http.post(`${BASE}/runs/move`, () =>
    HttpResponse.json({ ok: true, moved_count: 0, failed_count: 0, moved: [], failed: [] }),
  ),
  http.delete(`${BASE}/runs/:id/permanent`, () =>
    HttpResponse.json({ success: true }),
  ),
  http.post(`${BASE}/runs/permanent-delete`, () =>
    HttpResponse.json({ deleted_count: 0, total_runs: 0, total_blobs_deleted: 0, total_bytes_freed: 0, dry_run: false, results: {} }),
  ),

  // ── Recycle bin ──
  http.get(`${BASE}/recycle-bin`, () =>
    HttpResponse.json({ deleted_runs: [] }),
  ),
  http.post(`${BASE}/recycle-bin/restore`, () =>
    HttpResponse.json({ restored_count: 0, results: {}, message: 'ok' }),
  ),
  http.post(`${BASE}/recycle-bin/empty`, () =>
    HttpResponse.json({ permanently_deleted: 0, message: 'ok' }),
  ),

  // ── Config ──
  http.get(`${BASE}/config`, () =>
    HttpResponse.json({
      user_root_dir: '/tmp',
      storage: '/tmp/runicorn',
      home_directory: '/tmp',
      storage_backend: {
        mode: 'sqlite',
        label: 'SQLite-backed',
        available: true,
        backend_class: 'SQLiteStorageBackend',
      },
    }),
  ),
  http.post(`${BASE}/config/user_root_dir`, () =>
    HttpResponse.json({ ok: true, user_root_dir: '/tmp', storage: '/tmp/runicorn' }),
  ),
  http.get(`${BASE}/config/storage-candidates`, () =>
    HttpResponse.json({
      scan_root: '/tmp',
      max_depth: 3,
      candidates: [],
    }),
  ),
  http.get(`${BASE}/config/column-widths`, () =>
    HttpResponse.json({ widths: {} }),
  ),
  http.post(`${BASE}/config/column-widths`, () =>
    HttpResponse.json({ ok: true }),
  ),

  // ── Preferences ──
  http.get(`${BASE}/config/dismissed-alerts`, () =>
    HttpResponse.json({ dismissed_alerts: [] }),
  ),
  http.post(`${BASE}/config/dismissed-alerts/dismiss`, () =>
    HttpResponse.json({ ok: true }),
  ),
  http.post(`${BASE}/config/dismissed-alerts/undismiss`, () =>
    HttpResponse.json({ ok: true }),
  ),
  http.post(`${BASE}/config/dismissed-alerts/clear`, () =>
    HttpResponse.json({ ok: true }),
  ),

  // ── Projects / Paths ──
  http.get(`${BASE}/projects`, () =>
    HttpResponse.json({ projects: [] }),
  ),
  http.get(`${BASE}/paths`, () =>
    HttpResponse.json({ paths: [] }),
  ),
  http.post(`${BASE}/paths/soft-delete`, () =>
    HttpResponse.json({ deleted_count: 0 }),
  ),
  http.post(`${BASE}/paths/create`, () =>
    HttpResponse.json({ ok: true, path: '' }),
  ),

  // ── Import ──
  http.post(`${BASE}/import/preview`, () =>
    HttpResponse.json({ ok: true, token: 'tok', filename: 'f.zip', runs: [], total_runs: 0, total_files: 0, conflict_count: 0, conflict_run_ids: [] }),
  ),
  http.post(`${BASE}/import/archive`, () =>
    HttpResponse.json({ ok: true, imported_files: 0, new_run_dirs: [], new_run_ids: [], skipped_run_ids: [], skipped_count: 0, storage: '', mode: 'merge', isolate_base: null }),
  ),

  // ── Status ──
  http.post(`${BASE}/status/check`, () =>
    HttpResponse.json({ checked: 0, updated: 0, message: 'ok' }),
  ),

  // ── GPU ──
  http.get(`${BASE}/gpu/telemetry`, () =>
    HttpResponse.json({ available: false }),
  ),
  http.get(`${BASE}/gpu/telemetry/history`, () =>
    HttpResponse.json({ available: false, enabled: false, samples: [] }),
  ),
  http.get(`${BASE}/gpu/telemetry/config`, () =>
    HttpResponse.json({ enabled: false, interval_sec: 5, max_duration_h: 24 }),
  ),
  http.post(`${BASE}/gpu/telemetry/config`, () =>
    HttpResponse.json({ ok: true, enabled: false, interval_sec: 5, max_duration_h: 24 }),
  ),

  // ── System ──
  http.get(`${BASE}/system/monitor`, () =>
    HttpResponse.json({}),
  ),

  // ── Storage ──
  http.get(`${BASE}/storage/stats`, () =>
    HttpResponse.json({
      storage_root: '',
      total: { size_bytes: 0, size_human: '0 B' },
      archive: {
        size_bytes: 0,
        size_human: '0 B',
        blobs: { size_bytes: 0, size_human: '0 B', file_count: 0 },
        manifests: { size_bytes: 0, size_human: '0 B', file_count: 0, by_category: {} },
        outputs: { size_bytes: 0, size_human: '0 B', file_count: 0 },
      },
      runs: { size_bytes: 0, size_human: '0 B', projects_count: 0, experiments_count: 0, runs_count: 0 },
      index: { size_bytes: 0, size_human: '0 B' },
    }),
  ),

  // ── Remote ──
  http.post(`${BASE}/remote/connect`, () =>
    HttpResponse.json({ host: 'test', port: 22, username: 'user', status: 'connected', connectedAt: Date.now() }),
  ),
  http.post(`${BASE}/remote/disconnect`, () =>
    HttpResponse.json({ ok: true }),
  ),
  http.get(`${BASE}/remote/sessions`, () =>
    HttpResponse.json({ sessions: [] }),
  ),
  http.post(`${BASE}/remote/viewer/start`, () =>
    HttpResponse.json({ sessionId: 's1', host: 'test', status: 'running' }),
  ),
  http.post(`${BASE}/remote/viewer/stop`, () =>
    HttpResponse.json({ ok: true }),
  ),
  http.get(`${BASE}/remote/viewer/sessions`, () =>
    HttpResponse.json({ sessions: [] }),
  ),

  // ── SSH ──
  http.get(`${BASE}/config/ssh_connections`, () =>
    HttpResponse.json({ connections: [] }),
  ),
]
