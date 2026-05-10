import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../__mocks__/server'
import { renderWithProviders } from './helpers'
import ExperimentPage from '../pages/ExperimentPage'

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

// Stub heavy child components that are not under test
vi.mock('../components/PathTreePanel', () => ({
  default: () => <div data-testid="path-tree-panel" />,
}))
vi.mock('../components/CompareRunsPanel', () => ({
  default: () => <div data-testid="compare-runs-panel" />,
}))
vi.mock('../components/CompareChartsView', () => ({
  default: () => <div data-testid="compare-charts-view" />,
}))
vi.mock('../components/AddTagModal', () => ({
  default: () => null,
}))
vi.mock('../components/RecycleBin', () => ({
  default: () => null,
}))
vi.mock('../components/ResizableTitle', () => ({
  default: (props: any) => <th {...props} />,
}))
vi.mock('../components/LoadingSkeleton', () => ({
  ExperimentListSkeleton: () => <div data-testid="skeleton" />,
}))
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => children,
}))

// ── Sample data ──

const sampleRuns = [
  {
    id: 'run_alpha',
    path: 'proj/train',
    alias: 'baseline',
    tags: ['v1'],
    status: 'finished',
    created_time: 1700000000,
    summary: {},
    assets_count: 2,
  },
  {
    id: 'run_beta',
    path: 'proj/eval',
    alias: null,
    tags: [],
    status: 'running',
    created_time: 1700000100,
    summary: {},
    assets_count: 0,
  },
  {
    id: 'run_gamma',
    path: 'proj/test',
    alias: 'ablation',
    tags: ['v2'],
    status: 'failed',
    created_time: 1700000200,
    summary: {},
    assets_count: 1,
  },
]

// ── Helpers ──

function renderPage() {
  return renderWithProviders(<ExperimentPage />, { initialEntries: ['/'] })
}

// ── Tests ──

describe('ExperimentPage integration', () => {
  it('renders Table with runs from msw /api/runs', async () => {
    server.use(
      http.get('/api/runs', () =>
        HttpResponse.json({ runs: sampleRuns }),
      ),
    )

    renderPage()

    // run_id column renders only the suffix after "_" (e.g. "alpha" for "run_alpha")
    // Use path column values which are rendered directly
    await waitFor(() => {
      expect(screen.getByText('proj/train')).toBeInTheDocument()
      expect(screen.getByText('proj/eval')).toBeInTheDocument()
      expect(screen.getByText('proj/test')).toBeInTheDocument()
    }, { timeout: 5000 })
  })

  it('search filter reduces visible rows', async () => {
    server.use(
      http.get('/api/runs', () =>
        HttpResponse.json({ runs: sampleRuns }),
      ),
    )

    renderPage()

    // Wait for table to load — match on path values
    await waitFor(() => {
      expect(screen.getByText('proj/train')).toBeInTheDocument()
    }, { timeout: 5000 })

    // Type in search box — search matches run_id, alias, tags
    // "baseline" matches the alias of run_alpha
    const searchInput = screen.getByPlaceholderText('experiments.search_placeholder')
    await userEvent.type(searchInput, 'baseline')

    // Only the matching run should remain visible
    await waitFor(() => {
      expect(screen.getByText('proj/train')).toBeInTheDocument()
      expect(screen.queryByText('proj/eval')).not.toBeInTheDocument()
      expect(screen.queryByText('proj/test')).not.toBeInTheDocument()
    })
  })

  it('selecting rows shows batch action buttons', { timeout: 15000 }, async () => {
    server.use(
      http.get('/api/runs', () =>
        HttpResponse.json({ runs: sampleRuns }),
      ),
    )

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('proj/train')).toBeInTheDocument()
    }, { timeout: 5000 })

    // Initially batch actions should be hidden
    expect(screen.queryByText(/experiments\.compare/)).not.toBeInTheDocument()

    // Click "select all" checkbox in the table header
    // checkboxes[0] is the autoRefresh checkbox in FilterToolbar
    // checkboxes[1] is the table header "select all" checkbox
    const checkboxes = screen.getAllByRole('checkbox')
    await userEvent.click(checkboxes[1])

    // Batch action buttons should now appear
    await waitFor(() => {
      expect(screen.getByText(/experiments\.compare/)).toBeInTheDocument()
      expect(screen.getByText(/experiments\.export/)).toBeInTheDocument()
      expect(screen.getByText(/experiments\.delete/)).toBeInTheDocument()
    })
  })
})
