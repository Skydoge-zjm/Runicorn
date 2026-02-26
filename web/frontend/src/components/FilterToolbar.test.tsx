import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FilterToolbar from './FilterToolbar'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: vi.fn() },
  }),
}))

const baseProps = {
  searchText: '',
  onSearchChange: vi.fn(),
  projectFilter: 'all',
  onProjectFilterChange: vi.fn(),
  statusFilter: 'all',
  onStatusFilterChange: vi.fn(),
  projects: ['projA', 'projB'],
  treePanelCollapsed: false,
  onToggleTreePanel: vi.fn(),
  loading: false,
  autoRefresh: false,
  onRefresh: vi.fn(),
  onAutoRefreshChange: vi.fn(),
  selectedCount: 0,
  onCompare: vi.fn(),
  onDelete: vi.fn(),
  onExportZip: vi.fn(),
  onOpenRecycleBin: vi.fn(),
}

describe('FilterToolbar', () => {
  it('renders search input, refresh button', () => {
    render(<FilterToolbar {...baseProps} />)
    expect(screen.getByPlaceholderText('experiments.search_placeholder')).toBeInTheDocument()
    expect(screen.getByText('runs.refresh')).toBeInTheDocument()
  })

  it('search input triggers onSearchChange', async () => {
    const onSearchChange = vi.fn()
    render(<FilterToolbar {...baseProps} onSearchChange={onSearchChange} />)
    const input = screen.getByPlaceholderText('experiments.search_placeholder')
    await userEvent.type(input, 'hello')
    expect(onSearchChange).toHaveBeenCalled()
  })

  it('hides batch action buttons when selectedCount === 0', () => {
    render(<FilterToolbar {...baseProps} selectedCount={0} />)
    expect(screen.queryByText(/experiments\.compare/)).not.toBeInTheDocument()
    expect(screen.queryByText(/experiments\.export/)).not.toBeInTheDocument()
    expect(screen.queryByText(/experiments\.delete/)).not.toBeInTheDocument()
  })

  it('shows batch action buttons when selectedCount > 0', () => {
    render(<FilterToolbar {...baseProps} selectedCount={3} />)
    expect(screen.getByText(/experiments\.compare/)).toBeInTheDocument()
    expect(screen.getByText(/experiments\.export/)).toBeInTheDocument()
    expect(screen.getByText(/experiments\.delete/)).toBeInTheDocument()
  })

  it('Compare button is disabled when selectedCount < 2', () => {
    render(<FilterToolbar {...baseProps} selectedCount={1} />)
    const btn = screen.getByText(/experiments\.compare/).closest('button')
    expect(btn).toBeDisabled()
  })

  it('autoRefresh checkbox triggers onAutoRefreshChange', async () => {
    const onAutoRefreshChange = vi.fn()
    render(<FilterToolbar {...baseProps} onAutoRefreshChange={onAutoRefreshChange} />)
    const checkbox = screen.getByText('experiments.auto_refresh')
    await userEvent.click(checkbox)
    expect(onAutoRefreshChange).toHaveBeenCalled()
  })
})
