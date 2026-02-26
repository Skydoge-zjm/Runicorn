import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../__mocks__/server'
import {
  getDismissedAlerts,
  dismissAlert,
  undismissAlert,
} from '../preferences'

describe('getDismissedAlerts', () => {
  it('returns array of alert IDs', async () => {
    server.use(
      http.get('/api/config/dismissed-alerts', () =>
        HttpResponse.json({ dismissed_alerts: ['a1', 'a2'] }),
      ),
    )
    const alerts = await getDismissedAlerts()
    expect(alerts).toEqual(['a1', 'a2'])
  })

  it('returns empty array when none dismissed', async () => {
    const alerts = await getDismissedAlerts()
    expect(alerts).toEqual([])
  })
})

describe('dismissAlert', () => {
  it('sends POST with alert_id', async () => {
    await expect(dismissAlert('test-alert')).resolves.toBeUndefined()
  })

  it('throws on non-ok response', async () => {
    server.use(
      http.post('/api/config/dismissed-alerts/dismiss', () =>
        new HttpResponse('fail', { status: 500 }),
      ),
    )
    await expect(dismissAlert('x')).rejects.toThrow('Failed to dismiss alert')
  })
})

describe('undismissAlert', () => {
  it('sends POST with alert_id', async () => {
    await expect(undismissAlert('test-alert')).resolves.toBeUndefined()
  })

  it('throws on non-ok response', async () => {
    server.use(
      http.post('/api/config/dismissed-alerts/undismiss', () =>
        new HttpResponse('fail', { status: 500 }),
      ),
    )
    await expect(undismissAlert('x')).rejects.toThrow('Failed to undismiss alert')
  })
})
