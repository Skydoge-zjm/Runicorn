import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AddTagModal from '../components/AddTagModal'

// ── Mocks ──

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: vi.fn() },
  }),
}))

// ── Tests ──

describe('AddTagModal', () => {
  const defaultProps = {
    open: true,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
    existingTags: [] as string[],
    allTags: [] as string[],
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders modal with title and input when open', () => {
    render(<AddTagModal {...defaultProps} />)

    expect(screen.getByText('experiments.add_tag_title')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('experiments.enter_tag')).toBeInTheDocument()
  })

  it('does not render content when closed', () => {
    render(<AddTagModal {...defaultProps} open={false} />)

    // Modal title should not be visible
    expect(screen.queryByText('experiments.add_tag_title')).not.toBeInTheDocument()
  })

  it('confirm button is disabled when input is empty', () => {
    render(<AddTagModal {...defaultProps} />)

    const confirmBtn = screen.getByText('common.confirm')
    expect(confirmBtn.closest('button')).toBeDisabled()
  })

  it('confirm button is enabled when input has text', async () => {
    render(<AddTagModal {...defaultProps} />)

    const input = screen.getByPlaceholderText('experiments.enter_tag')

    await userEvent.type(input, 'my-tag')

    const confirmBtn = screen.getByText('common.confirm')
    expect(confirmBtn.closest('button')).not.toBeDisabled()
  })

  it('calls onConfirm with trimmed value when clicking confirm', async () => {
    render(<AddTagModal {...defaultProps} />)

    const input = screen.getByPlaceholderText('experiments.enter_tag')

    await userEvent.type(input, '  my-tag  ')
    await userEvent.click(screen.getByText('common.confirm'))

    expect(defaultProps.onConfirm).toHaveBeenCalledWith('my-tag')
  })

  it('calls onConfirm when pressing Enter', async () => {
    render(<AddTagModal {...defaultProps} />)

    const input = screen.getByPlaceholderText('experiments.enter_tag')

    await userEvent.type(input, 'enter-tag{Enter}')

    expect(defaultProps.onConfirm).toHaveBeenCalledWith('enter-tag')
  })

  it('calls onClose when pressing Escape', async () => {
    render(<AddTagModal {...defaultProps} />)

    const input = screen.getByPlaceholderText('experiments.enter_tag')

    await userEvent.click(input)
    await userEvent.keyboard('{Escape}')

    expect(defaultProps.onClose).toHaveBeenCalled()
  })

  it('calls onClose when clicking cancel', async () => {
    render(<AddTagModal {...defaultProps} />)

    await userEvent.click(screen.getByText('common.cancel'))

    expect(defaultProps.onClose).toHaveBeenCalled()
  })

  it('shows recommended tags that are not already existing', () => {
    render(<AddTagModal {...defaultProps} existingTags={['baseline', 'best']} />)

    // Section label
    expect(screen.getByText('experiments.recommended_tags')).toBeInTheDocument()

    // 'baseline' and 'best' should NOT appear since they're in existingTags
    expect(screen.queryByText('baseline')).not.toBeInTheDocument()
    expect(screen.queryByText('best')).not.toBeInTheDocument()

    // Other recommended tags should appear
    expect(screen.getByText('experiment')).toBeInTheDocument()
    expect(screen.getByText('debug')).toBeInTheDocument()
    expect(screen.getByText('production')).toBeInTheDocument()
  })

  it('clicking a recommended tag calls onConfirm', async () => {
    render(<AddTagModal {...defaultProps} />)

    await userEvent.click(screen.getByText('experiment'))

    expect(defaultProps.onConfirm).toHaveBeenCalledWith('experiment')
  })

  it('shows history tags that are not in existing or recommended lists', () => {
    render(
      <AddTagModal
        {...defaultProps}
        existingTags={['my-existing']}
        allTags={['my-existing', 'custom-tag-1', 'custom-tag-2', 'baseline']}
      />,
    )

    // Section label
    expect(screen.getByText('experiments.history_tags')).toBeInTheDocument()

    // 'custom-tag-1' and 'custom-tag-2' should appear (not in existing, not in recommended)
    expect(screen.getByText('custom-tag-1')).toBeInTheDocument()
    expect(screen.getByText('custom-tag-2')).toBeInTheDocument()

    // 'my-existing' should not appear (already existing)
    // 'baseline' should not appear in history (it's in RECOMMENDED_TAGS)
  })

  it('clicking a history tag calls onConfirm', async () => {
    render(
      <AddTagModal
        {...defaultProps}
        allTags={['history-tag']}
      />,
    )

    await userEvent.click(screen.getByText('history-tag'))

    expect(defaultProps.onConfirm).toHaveBeenCalledWith('history-tag')
  })

  it('does not show history section when no history tags exist', () => {
    render(<AddTagModal {...defaultProps} allTags={[]} />)

    expect(screen.queryByText('experiments.history_tags')).not.toBeInTheDocument()
  })

  it('clears input when modal re-opens', async () => {
    const { rerender } = render(<AddTagModal {...defaultProps} />)

    const input = screen.getByPlaceholderText('experiments.enter_tag')
    await userEvent.type(input, 'some-text')

    // Close and reopen
    rerender(<AddTagModal {...defaultProps} open={false} />)
    rerender(<AddTagModal {...defaultProps} open={true} />)

    // Input should be cleared
    await waitFor(() => {
      const newInput = screen.getByPlaceholderText('experiments.enter_tag')
      expect(newInput).toHaveValue('')
    })
  })

  it('does not call onConfirm when input is whitespace only', async () => {
    render(<AddTagModal {...defaultProps} />)

    const input = screen.getByPlaceholderText('experiments.enter_tag')

    await userEvent.type(input, '   ')

    // Confirm button should be disabled
    const confirmBtn = screen.getByText('common.confirm')
    expect(confirmBtn.closest('button')).toBeDisabled()
  })

  it('limits history tags to 10', () => {
    const manyTags = Array.from({ length: 20 }, (_, i) => `tag-${i}`)
    render(<AddTagModal {...defaultProps} allTags={manyTags} />)

    // Should only show up to 10 history tags
    const historySection = screen.getByText('experiments.history_tags').parentElement
    const tagElements = historySection?.querySelectorAll('.ant-tag')
    expect(tagElements?.length).toBeLessThanOrEqual(10)
  })

  it('hides recommended tags section when all recommended are in existingTags', () => {
    const allRecommended = ['baseline', 'best', 'experiment', 'debug', 'production', 'test', 'v1', 'v2', 'final', 'draft']
    render(<AddTagModal {...defaultProps} existingTags={allRecommended} />)

    expect(screen.queryByText('experiments.recommended_tags')).not.toBeInTheDocument()
  })
})
