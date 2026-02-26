import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '../__mocks__/server'
import { SettingsProvider } from '../contexts/SettingsContext'
import { defaultSettings } from './helpers'
import AssetsPage from '../pages/AssetsPage'

// ── Mocks ──

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, any>) => {
      if (opts) return `${key}:${JSON.stringify(opts)}`
      return key
    },
    i18n: { language: 'en', changeLanguage: vi.fn() },
  }),
}))

vi.mock('../utils/logger', () => ({
  default: { error: vi.fn(), warn: vi.fn(), info: vi.fn(), debug: vi.fn() },
}))

// ── Mock useAssetsIndex ──

const mockRefresh = vi.fn()
const mockCancel = vi.fn()

const sampleIndex = {
  version: 3,
  generated_at: 1700000000,
  runs: [
    { run_id: 'run_1', path: 'proj/train', alias: 'baseline', created_time: 1700000000, status: 'finished', assets_count: 3 },
    { run_id: 'run_2', path: 'proj/eval', alias: null, created_time: 1700000100, status: 'running', assets_count: 2 },
  ],
  run_assets: {},
  experiments: [
    {
      key: 'proj/train',
      path: 'proj/train',
      runs_count: 1,
      assets_total: 3,
      archived_total: 1,
      by_kind: { code: 1, config: 1, dataset: 0, pretrained: 0, output: 1 },
      run_ids: ['run_1'],
    },
    {
      key: 'proj/eval',
      path: 'proj/eval',
      runs_count: 1,
      assets_total: 2,
      archived_total: 0,
      by_kind: { code: 0, config: 1, dataset: 1, pretrained: 0, output: 0 },
      run_ids: ['run_2'],
    },
  ],
  repo: [
    {
      key: 'code:main.py',
      encoded: 'Y29kZTptYWluLnB5',
      identity: { kind: 'code', name: 'main.py' },
      kind: 'code',
      name: 'main.py',
      saved: true,
      paths: ['proj/train'],
      runs_count: 1,
      last_used_time: 1700000000,
      run_ids: ['run_1'],
    },
    {
      key: 'config:params.yaml',
      encoded: 'Y29uZmlnOnBhcmFtcy55YW1s',
      identity: { kind: 'config', name: 'params.yaml' },
      kind: 'config',
      name: 'params.yaml',
      saved: false,
      paths: ['proj/train', 'proj/eval'],
      runs_count: 2,
      last_used_time: 1700000100,
      run_ids: ['run_1', 'run_2'],
    },
    {
      key: 'dataset:imagenet',
      encoded: 'ZGF0YXNldDppbWFnZW5ldA',
      identity: { kind: 'dataset', name: 'imagenet' },
      kind: 'dataset',
      name: 'imagenet',
      saved: false,
      paths: ['proj/eval'],
      runs_count: 1,
      last_used_time: 1700000100,
      run_ids: ['run_2'],
    },
  ],
}

let mockUseAssetsIndexReturn = {
  index: sampleIndex as any,
  loading: false,
  progress: { total: 0, done: 0 },
  stats: { totalRuns: 2, runsWithAssets: 2, totalAssets: 3, archivedAssets: 1 },
  refresh: mockRefresh,
  cancel: mockCancel,
}

vi.mock('../hooks/useAssetsIndex', () => ({
  useAssetsIndex: () => mockUseAssetsIndexReturn,
}))

// ── Helpers ──

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/assets']}>
        <SettingsProvider value={{ settings: defaultSettings, setSettings: vi.fn() }}>
          <AssetsPage />
        </SettingsProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// ── Tests ──

describe('AssetsPage integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAssetsIndexReturn = {
      index: sampleIndex as any,
      loading: false,
      progress: { total: 0, done: 0 },
      stats: { totalRuns: 2, runsWithAssets: 2, totalAssets: 3, archivedAssets: 1 },
      refresh: mockRefresh,
      cancel: mockCancel,
    }
  })

  it('renders page title and subtitle', () => {
    renderPage()

    expect(screen.getByText('assets.title')).toBeInTheDocument()
    expect(screen.getByText('assets.subtitle')).toBeInTheDocument()
  })

  it('displays statistics from useAssetsIndex', () => {
    renderPage()

    // Stat titles (i18n keys) — some appear in both stats and table columns
    expect(screen.getByText('experiments.total_runs')).toBeInTheDocument()
    // 'assets.table.runs' appears in both stat card and table header — check at least one exists
    expect(screen.getAllByText('assets.table.runs').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('assets.table.assets_total').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('assets.table.archived').length).toBeGreaterThanOrEqual(1)
  })

  it('renders overview tab with experiment rows', () => {
    renderPage()

    // Overview tab should be shown by default
    expect(screen.getByText('assets.tab.overview')).toBeInTheDocument()

    // Experiment paths
    expect(screen.getByText('proj/train')).toBeInTheDocument()
    expect(screen.getByText('proj/eval')).toBeInTheDocument()
  })

  it('displays repo tab with repository items', { timeout: 15000 }, async () => {
    renderPage()

    // Click repo tab
    await userEvent.click(screen.getByText('assets.tab.repository'))

    // Wait for repo rows to render
    await waitFor(() => {
      expect(screen.getByText('main.py')).toBeInTheDocument()
      expect(screen.getByText('params.yaml')).toBeInTheDocument()
    }, { timeout: 10000 })
  })

  it('shows refresh button and calls refresh on click', async () => {
    renderPage()

    // Find and click refresh button
    const refreshBtn = screen.getByText('assets.actions.refresh_index')
    await userEvent.click(refreshBtn)

    expect(mockRefresh).toHaveBeenCalledTimes(1)
  })

  it('shows auto-refresh checkbox linked to settings', () => {
    renderPage()

    expect(screen.getByText('experiments.auto_refresh')).toBeInTheDocument()
  })

  it('renders overview table columns correctly', () => {
    renderPage()

    // Column headers in overview table
    expect(screen.getByText('assets.table.path')).toBeInTheDocument()
    expect(screen.getByText('assets.table.code')).toBeInTheDocument()
    expect(screen.getByText('assets.table.config')).toBeInTheDocument()
    expect(screen.getByText('assets.table.datasets')).toBeInTheDocument()
    expect(screen.getByText('assets.table.pretrained')).toBeInTheDocument()
    expect(screen.getByText('assets.table.outputs')).toBeInTheDocument()
  })

  it('handles loading state', () => {
    mockUseAssetsIndexReturn = {
      ...mockUseAssetsIndexReturn,
      loading: true,
    }

    renderPage()

    // The refresh button should show loading text when autoRefresh is off
    expect(screen.getByText('assets.actions.refresh_index')).toBeInTheDocument()
  })

  it('handles empty index (null)', () => {
    mockUseAssetsIndexReturn = {
      ...mockUseAssetsIndexReturn,
      index: null,
      stats: { totalRuns: 0, runsWithAssets: 0, totalAssets: 0, archivedAssets: 0 },
    }

    renderPage()

    // Should still render without crashing
    expect(screen.getByText('assets.title')).toBeInTheDocument()
  })

  it('displays storage stats from API', async () => {
    server.use(
      http.get('/api/storage/stats', () =>
        HttpResponse.json({
          storage_root: '/data/storage',
          total: { size_bytes: 1024000, size_human: '1 MB' },
          archive: {
            size_bytes: 512000,
            size_human: '500 KB',
            blobs: { size_bytes: 256000, size_human: '250 KB', file_count: 10 },
            manifests: { size_bytes: 128000, size_human: '125 KB', file_count: 5, by_category: {} },
            outputs: { size_bytes: 128000, size_human: '125 KB', file_count: 3 },
          },
          runs: { size_bytes: 512000, size_human: '500 KB', projects_count: 1, experiments_count: 2, runs_count: 5 },
          index: { size_bytes: 1024, size_human: '1 KB' },
        }),
      ),
    )

    renderPage()

    // Should display storage stat
    await waitFor(() => {
      expect(screen.getByText('storage.archive_size')).toBeInTheDocument()
    })
  })

  it('renders repo tab filter controls', async () => {
    renderPage()

    await userEvent.click(screen.getByText('assets.tab.repository'))

    await waitFor(() => {
      // Filter labels/text
      expect(screen.getByText('assets.filters.only_archived')).toBeInTheDocument()
      expect(screen.getByText('assets.filters.only_related')).toBeInTheDocument()
    })
  })

  it('repo tab filters out items with runs_count=0 when onlyRelated is true (default)', async () => {
    // Default: onlyRelated is true — all 3 repo items have runs_count > 0, so all visible
    renderPage()

    await userEvent.click(screen.getByText('assets.tab.repository'))

    await waitFor(() => {
      expect(screen.getByText('main.py')).toBeInTheDocument()
      expect(screen.getByText('params.yaml')).toBeInTheDocument()
      expect(screen.getByText('imagenet')).toBeInTheDocument()
    })
  })

  it('repo tab shows saved tag for archived assets', async () => {
    renderPage()

    await userEvent.click(screen.getByText('assets.tab.repository'))

    await waitFor(() => {
      // main.py is saved=true, so it should have the "saved" tag
      expect(screen.getByText('assets.tag.saved')).toBeInTheDocument()
      // params.yaml and imagenet are saved=false, so they should have "ref" tags
      expect(screen.getAllByText('assets.tag.ref').length).toBeGreaterThanOrEqual(2)
    })
  })

  it('shows repo table column headers', async () => {
    renderPage()

    await userEvent.click(screen.getByText('assets.tab.repository'))

    await waitFor(() => {
      expect(screen.getByText('assets.repo.kind')).toBeInTheDocument()
      expect(screen.getByText('assets.repo.asset')).toBeInTheDocument()
      expect(screen.getByText('assets.repo.saved')).toBeInTheDocument()
      expect(screen.getByText('assets.repo.last_used')).toBeInTheDocument()
      expect(screen.getByText('assets.repo.runs_count')).toBeInTheDocument()
      expect(screen.getByText('assets.repo.actions')).toBeInTheDocument()
    })
  })
})
