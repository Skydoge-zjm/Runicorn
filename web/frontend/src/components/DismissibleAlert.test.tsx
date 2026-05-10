import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../__mocks__/server'
import DismissibleAlert from './DismissibleAlert'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: vi.fn() },
  }),
}))

describe('DismissibleAlert', () => {
  it('renders alert content after loading', async () => {
    render(
      <DismissibleAlert alertId="test-1" message="Hello Alert" type="info" />,
    )

    await waitFor(() => {
      expect(screen.getByText('Hello Alert')).toBeInTheDocument()
    })
  })

  it('calls dismiss API on close when "don\'t show again" is checked', async () => {
    let dismissCalled = false
    server.use(
      http.post('/api/config/dismissed-alerts/dismiss', () => {
        dismissCalled = true
        return HttpResponse.json({ ok: true })
      }),
    )

    render(
      <DismissibleAlert alertId="test-2" message="Dismissable" type="warning" />,
    )

    await waitFor(() => {
      expect(screen.getByText('Dismissable')).toBeInTheDocument()
    })

    // Check "don't show again"
    const checkbox = screen.getByText('common.dontShowAgain')
    await userEvent.click(checkbox)

    // Close the alert
    const closeBtn = screen.getByRole('button', { name: /close/i })
    await userEvent.click(closeBtn)

    await waitFor(() => {
      expect(dismissCalled).toBe(true)
    })
  })

  it('does not render if alert was previously dismissed', async () => {
    server.use(
      http.get('/api/config/dismissed-alerts', () =>
        HttpResponse.json({ dismissed_alerts: ['already-dismissed'] }),
      ),
    )

    render(
      <DismissibleAlert alertId="already-dismissed" message="Should not show" type="info" />,
    )

    await waitFor(() => {
      expect(screen.queryByText('Should not show')).not.toBeInTheDocument()
    })
  })
})
