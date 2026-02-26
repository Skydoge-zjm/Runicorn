import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConfigProvider } from 'antd'
import StatsBar from './StatsBar'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: vi.fn() },
  }),
}))

function renderStatsBar(stats: { total: number; running: number; finished: number; failed: number }) {
  return render(
    <ConfigProvider>
      <StatsBar stats={stats} />
    </ConfigProvider>,
  )
}

describe('StatsBar', () => {
  it('renders all four stat numbers', () => {
    renderStatsBar({ total: 10, running: 3, finished: 5, failed: 2 })
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('renders correctly with all zeros', () => {
    renderStatsBar({ total: 0, running: 0, finished: 0, failed: 0 })
    const zeros = screen.getAllByText('0')
    expect(zeros.length).toBe(4)
  })

  it('numbers match passed props', () => {
    renderStatsBar({ total: 42, running: 7, finished: 30, failed: 5 })
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText('30')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
  })
})
