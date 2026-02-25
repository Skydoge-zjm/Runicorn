/**
 * Dismissible Alert Component
 * 
 * Alert that can be permanently dismissed with "Don't show again" checkbox
 */

import { useState, useEffect } from 'react'
import { Alert, Checkbox } from 'antd'
import type { AlertProps } from 'antd'
import { useTranslation } from 'react-i18next'
import { dismissAlert, getDismissedAlerts } from '../api/preferences'

interface DismissibleAlertProps extends Omit<AlertProps, 'closable' | 'onClose'> {
  /** Unique alert ID for dismissal tracking */
  alertId: string
  /** Show "Don't show again" checkbox */
  showDismissOption?: boolean
  /** Callback when alert is permanently dismissed */
  onDismiss?: () => void
}

export default function DismissibleAlert({
  alertId,
  showDismissOption = true,
  onDismiss,
  ...alertProps
}: DismissibleAlertProps) {
  const { t } = useTranslation()
  const [loaded, setLoaded] = useState(false)
  const [visible, setVisible] = useState(true)
  const [dontShowAgain, setDontShowAgain] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  // Check if alert was previously dismissed
  useEffect(() => {
    let active = true
    const checkDismissed = async () => {
      try {
        const dismissedAlerts = await getDismissedAlerts()
        if (!active) return
        if (dismissedAlerts.includes(alertId)) {
          setDismissed(true)
          setVisible(false)
        }
      } catch (error) {
        console.error('Failed to check dismissed alerts:', error)
      }
      if (active) setLoaded(true)
    }
    checkDismissed()
    return () => { active = false }
  }, [alertId])

  const handleClose = async () => {
    setVisible(false)
    
    if (dontShowAgain) {
      try {
        await dismissAlert(alertId)
        setDismissed(true)
        onDismiss?.()
      } catch (error) {
        console.error('Failed to dismiss alert:', error)
      }
    }
  }

  // Don't render until check completes, or if dismissed
  if (!loaded || dismissed || !visible) {
    return null
  }

  return (
    <Alert
      {...alertProps}
      closable
      onClose={handleClose}
      action={
        showDismissOption ? (
          <div style={{ marginTop: -4 }}>
            <Checkbox
              checked={dontShowAgain}
              onChange={(e) => setDontShowAgain(e.target.checked)}
              onClick={(e) => e.stopPropagation()}
            >
              <span style={{ fontSize: '12px' }}>
                {t('common.dontShowAgain')}
              </span>
            </Checkbox>
          </div>
        ) : undefined
      }
    />
  )
}
