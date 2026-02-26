import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '../__mocks__/server'
import { SettingsProvider } from '../contexts/SettingsContext'
import { defaultSettings } from './helpers'
import RunDetailPage from '../pages/RunDetailPage'

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

// Stub heavy child components
vi.mock('../components/LogsViewer', () => ({
  default: ({ url }: { url: string }) => <div data-testid="logs-viewer" data-url={url} />,
}))
vi.mock('../components/MetricChart', () => ({
  default: ({ title }: { title: string }) => <div data-testid={`metric-chart-${title}`}>{title}</div>,
}))
vi.mock('../components/RunAssets', () => ({
  default: ({ runId }: { runId: string }) => <div data-testid="run-assets" data-run-id={runId} />,
}))
vi.mock('../components/LazyChartWrapper', () => ({
  default: ({ children }: { children: React.ReactNode }) => <div data-testid="lazy-chart">{children}</div>,
}))
vi.mock('../components/ErrorBoundary', () => ({
  default: ({ children }: { children: React.ReactNode; fallback?: any }) => <>{children}</>,
}))
vi.mock('../components/LoadingSkeleton', () => ({
  RunDetailSkeleton: () => <div data-testid="run-detail-skeleton" />,
}))

// ── Sample data ──

const runDetail = {
  run_id: 'run_abc123',
  path: 'proj/experiment',
  alias: 'my-baseline',
  status: 'running',
  start_time: 1700000000,
  duration: 3600,
  pid: 12345,
  run_dir: '/data/runs/run_abc123',
  logs: '/data/runs/run_abc123/output.log',
  assets_count: 5,
  summary: { loss: 0.01 },
}

const stepMetrics = {
  columns: ['global_step', 'time', 'train_loss', 'val_loss', 'accuracy'],
  rows: [
    { global_step: 1, time: 1700000010, train_loss: 1.5, val_loss: 1.8, accuracy: 0.3 },
    { global_step: 2, time: 1700000020, train_loss: 1.2, val_loss: 1.5, accuracy: 0.5 },
    { global_step: 3, time: 1700000030, train_loss: 0.8, val_loss: 1.1, accuracy: 0.7 },
  ],
  total: 3,
}

// ── Helpers ──

function renderPage(runId = 'run_abc123') {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/runs/${runId}`]}>
        <SettingsProvider value={{ settings: defaultSettings, setSettings: vi.fn() }}>
          <Routes>
            <Route path="/runs/:id" element={<RunDetailPage />} />
          </Routes>
        </SettingsProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// ── Tests ──

describe('RunDetailPage integration', () => {
  beforeEach(() => {
    // Provide default handlers for the run detail page
    server.use(
      http.get('/api/runs/run_abc123', () => HttpResponse.json(runDetail)),
      http.get('/api/runs/run_abc123/metrics_step', () => HttpResponse.json(stepMetrics)),
    )
  })

  it('loads and displays run detail info', async () => {
    renderPage()

    // Should show alias as title
    await waitFor(() => {
      expect(screen.getByText('my-baseline')).toBeInTheDocument()
    }, { timeout: 5000 })

    // Status tag
    expect(screen.getByText('RUNNING')).toBeInTheDocument()

    // Path
    expect(screen.getByText('proj/experiment')).toBeInTheDocument()

    // PID
    expect(screen.getByText('PID: 12345')).toBeInTheDocument()
  })

  it('falls back to run_id when alias is null', async () => {
    server.use(
      http.get('/api/runs/run_noalias', () =>
        HttpResponse.json({ ...runDetail, run_id: 'run_noalias', alias: null }),
      ),
      http.get('/api/runs/run_noalias/metrics_step', () => HttpResponse.json(stepMetrics)),
    )

    renderPage('run_noalias')

    await waitFor(() => {
      expect(screen.getByText('run_noalias')).toBeInTheDocument()
    }, { timeout: 5000 })
  })

  it('displays three tabs: overview, logs, assets', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('my-baseline')).toBeInTheDocument()
    }, { timeout: 5000 })

    // Tab labels appear in both Tabs and Card titles — use role selectors for tabs
    const tabs = screen.getAllByRole('tab')
    expect(tabs.length).toBe(3)
    expect(tabs[0]).toHaveTextContent('run.tabs.overview')
    expect(tabs[1]).toHaveTextContent('logs.title')
    expect(tabs[2]).toHaveTextContent('run.assets.title')
  })

  it('renders metric charts for numeric columns', async () => {
    renderPage()

    // Wait for metrics to load and charts to appear
    await waitFor(() => {
      expect(screen.getByTestId('metric-chart-train_loss')).toBeInTheDocument()
      expect(screen.getByTestId('metric-chart-val_loss')).toBeInTheDocument()
      expect(screen.getByTestId('metric-chart-accuracy')).toBeInTheDocument()
    }, { timeout: 5000 })
  })

  it('does not render charts for skipped columns (global_step, time, etc.)', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByTestId('metric-chart-train_loss')).toBeInTheDocument()
    }, { timeout: 5000 })

    expect(screen.queryByTestId('metric-chart-global_step')).not.toBeInTheDocument()
    expect(screen.queryByTestId('metric-chart-time')).not.toBeInTheDocument()
  })

  it('shows "no metrics" alert when step metrics are empty', async () => {
    server.use(
      http.get('/api/runs/run_abc123/metrics_step', () =>
        HttpResponse.json({ columns: [], rows: [] }),
      ),
    )

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('metrics.none')).toBeInTheDocument()
    }, { timeout: 5000 })
  })

  it('renders RunAssets component in assets tab', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('my-baseline')).toBeInTheDocument()
    }, { timeout: 5000 })

    // RunAssets is mounted (display:none but in DOM) — verify it has the correct runId
    const runAssets = screen.getByTestId('run-assets')
    expect(runAssets).toBeInTheDocument()
    expect(runAssets).toHaveAttribute('data-run-id', 'run_abc123')
  })

  it('renders LogsViewer component in logs tab', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('my-baseline')).toBeInTheDocument()
    }, { timeout: 5000 })

    const logsViewer = screen.getByTestId('logs-viewer')
    expect(logsViewer).toBeInTheDocument()
    // URL should contain the run id
    expect(logsViewer.getAttribute('data-url')).toContain('run_abc123')
    expect(logsViewer.getAttribute('data-url')).toContain('/logs/ws')
  })

  it('shows skeleton during initial load', async () => {
    // Use a delayed response so we can catch the skeleton
    server.use(
      http.get('/api/runs/run_abc123', async () => {
        await new Promise((r) => setTimeout(r, 200))
        return HttpResponse.json(runDetail)
      }),
    )

    renderPage()

    // Skeleton should appear briefly
    expect(screen.getByTestId('run-detail-skeleton')).toBeInTheDocument()

    // Eventually the detail should load
    await waitFor(() => {
      expect(screen.getByText('my-baseline')).toBeInTheDocument()
    }, { timeout: 5000 })
  })

  it('shows stats: duration, total steps, assets count', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('my-baseline')).toBeInTheDocument()
    }, { timeout: 5000 })

    // Stat titles (i18n keys)
    expect(screen.getByText('run.stats.duration')).toBeInTheDocument()
    expect(screen.getByText('run.stats.total_steps')).toBeInTheDocument()
    expect(screen.getByText('run.stats.assets')).toBeInTheDocument()
  })

  it('handles different run statuses correctly', async () => {
    server.use(
      http.get('/api/runs/run_abc123', () =>
        HttpResponse.json({ ...runDetail, status: 'finished' }),
      ),
    )

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('FINISHED')).toBeInTheDocument()
    }, { timeout: 5000 })
  })

  it('handles failed status', async () => {
    server.use(
      http.get('/api/runs/run_abc123', () =>
        HttpResponse.json({ ...runDetail, status: 'failed' }),
      ),
    )

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('FAILED')).toBeInTheDocument()
    }, { timeout: 5000 })
  })

  it('shows refresh and compare buttons', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('my-baseline')).toBeInTheDocument()
    }, { timeout: 5000 })

    expect(screen.getByText('run.refresh')).toBeInTheDocument()
    expect(screen.getByText('run.compare_with')).toBeInTheDocument()
  })

  it('shows collapsible details section with expand label', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('my-baseline')).toBeInTheDocument()
    }, { timeout: 5000 })

    // The "More Details" collapse label should be visible (content hidden until expanded)
    expect(screen.getByText('run.more_details')).toBeInTheDocument()
  })

  it('does not crash when API returns error', async () => {
    server.use(
      http.get('/api/runs/run_abc123', () =>
        new HttpResponse('Internal Server Error', { status: 500 }),
      ),
    )

    renderPage()

    // The page should not crash — it will show skeleton since detail remains null
    await waitFor(() => {
      expect(screen.getByTestId('run-detail-skeleton')).toBeInTheDocument()
    })
  })
})
