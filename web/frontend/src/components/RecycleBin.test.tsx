import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import RecycleBin from './RecycleBin'

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

vi.mock('../api', () => ({
  listDeletedRuns: vi.fn().mockResolvedValue({ deleted_runs: [] }),
  restoreRuns: vi.fn().mockResolvedValue({ restored_count: 0, results: {}, message: 'ok' }),
  permanentDeleteRunsBatch: vi.fn().mockResolvedValue({ deleted_count: 0, total_blobs_deleted: 0 }),
  getRunAssetRefs: vi.fn().mockResolvedValue({ orphaned_assets: [], shared_assets: [], orphaned_count: 0, shared_count: 0 }),
}))

const sampleRuns = [
  { id: 'run_001', path: 'exp/train', alias: 'baseline', created_time: 1700000000, deleted_at: 1700100000, delete_reason: 'manual', original_status: 'finished', run_dir: '/tmp/runs/run_001' },
  { id: 'run_002', path: 'exp/eval', alias: null, created_time: 1700000100, deleted_at: 1700100100, delete_reason: 'manual', original_status: 'failed', run_dir: '/tmp/runs/run_002' },
]

describe('RecycleBin', () => {
  it('does not render Modal content when open=false', () => {
    render(<RecycleBin open={false} onClose={vi.fn()} />)
    expect(screen.queryByText('recycle_bin.title')).not.toBeInTheDocument()
  })

  it('renders Modal when open=true', async () => {
    render(<RecycleBin open={true} onClose={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText('recycle_bin.title')).toBeInTheDocument()
    })
  })

  it('displays deleted runs list after loading', async () => {
    const { listDeletedRuns } = await import('../api')
    vi.mocked(listDeletedRuns).mockResolvedValue({ deleted_runs: sampleRuns } as any)

    render(<RecycleBin open={true} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('run_001')).toBeInTheDocument()
      expect(screen.getByText('run_002')).toBeInTheDocument()
    })
  })

  it('Restore button is disabled when no runs are selected', async () => {
    const { listDeletedRuns } = await import('../api')
    vi.mocked(listDeletedRuns).mockResolvedValue({ deleted_runs: sampleRuns } as any)

    render(<RecycleBin open={true} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('run_001')).toBeInTheDocument()
    })

    const restoreBtn = screen.getByText(/recycle_bin\.restore_selected/).closest('button')!
    expect(restoreBtn).toBeDisabled()
  })

  it('shows empty state text when no deleted runs', async () => {
    render(<RecycleBin open={true} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('recycle_bin.empty_state')).toBeInTheDocument()
    })
  })
})
