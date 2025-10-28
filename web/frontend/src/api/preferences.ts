/**
 * API for user preferences (dismissed alerts, settings, etc.)
 */

const API_BASE = '/api/config'

/**
 * Get list of dismissed alert IDs
 */
export async function getDismissedAlerts(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/dismissed-alerts`)
  if (!response.ok) {
    throw new Error('Failed to get dismissed alerts')
  }
  const data = await response.json()
  return data.dismissed_alerts || []
}

/**
 * Dismiss an alert (won't show again)
 */
export async function dismissAlert(alertId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/dismissed-alerts/dismiss`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alert_id: alertId })
  })
  if (!response.ok) {
    throw new Error('Failed to dismiss alert')
  }
}

/**
 * Undismiss an alert (show again)
 */
export async function undismissAlert(alertId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/dismissed-alerts/undismiss`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alert_id: alertId })
  })
  if (!response.ok) {
    throw new Error('Failed to undismiss alert')
  }
}

/**
 * Clear all dismissed alerts
 */
export async function clearDismissedAlerts(): Promise<void> {
  const response = await fetch(`${API_BASE}/dismissed-alerts/clear`, {
    method: 'POST'
  })
  if (!response.ok) {
    throw new Error('Failed to clear dismissed alerts')
  }
}
