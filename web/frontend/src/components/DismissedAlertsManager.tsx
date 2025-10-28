/**
 * Dismissed Alerts Manager Component
 * 
 * Allows users to view and restore dismissed alerts in settings
 */

import React, { useState, useEffect } from 'react'
import { Card, List, Button, Space, Empty, message, Tooltip } from 'antd'
import { DeleteOutlined, ReloadOutlined, EyeOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { getDismissedAlerts, undismissAlert, clearDismissedAlerts } from '../api/preferences'

// Alert ID to human-readable name mapping
const ALERT_NAMES: Record<string, { zh: string, en: string }> = {
  'remote.intro': {
    zh: 'Remote Viewer 架构介绍',
    en: 'Remote Viewer Architecture Intro'
  },
  'remote.env.selectHint': {
    zh: '远程环境选择提示',
    en: 'Remote Environment Selection Hint'
  },
  'remote.env.checkRunicorn': {
    zh: 'Runicorn版本检查提示',
    en: 'Runicorn Version Check Hint'
  },
  'remote.config.pathNotExists': {
    zh: '存储路径不存在提示',
    en: 'Storage Path Not Exists Hint'
  },
}

export default function DismissedAlertsManager() {
  const { t, i18n } = useTranslation()
  const [dismissedAlerts, setDismissedAlerts] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const loadDismissedAlerts = async () => {
    setLoading(true)
    try {
      const alerts = await getDismissedAlerts()
      setDismissedAlerts(alerts)
    } catch (error) {
      message.error(t('settings.failedToLoadDismissedAlerts'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDismissedAlerts()
  }, [])

  const handleRestore = async (alertId: string) => {
    try {
      await undismissAlert(alertId)
      message.success(t('settings.alertRestored'))
      loadDismissedAlerts()
    } catch (error) {
      message.error(t('settings.failedToRestoreAlert'))
    }
  }

  const handleClearAll = async () => {
    try {
      await clearDismissedAlerts()
      message.success(t('settings.allAlertsRestored'))
      setDismissedAlerts([])
    } catch (error) {
      message.error(t('settings.failedToClearAlerts'))
    }
  }

  const getAlertName = (alertId: string) => {
    const names = ALERT_NAMES[alertId]
    if (names) {
      return i18n.language === 'zh' ? names.zh : names.en
    }
    return alertId
  }

  return (
    <Card
      title={t('settings.dismissedAlerts')}
      extra={
        dismissedAlerts.length > 0 && (
          <Button
            icon={<ReloadOutlined />}
            onClick={handleClearAll}
            size="small"
          >
            {t('settings.restoreAll')}
          </Button>
        )
      }
    >
      {dismissedAlerts.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('settings.noDismissedAlerts')}
        />
      ) : (
        <List
          dataSource={dismissedAlerts}
          loading={loading}
          renderItem={(alertId) => (
            <List.Item
              actions={[
                <Tooltip title={t('settings.restoreAlert')}>
                  <Button
                    type="text"
                    icon={<EyeOutlined />}
                    onClick={() => handleRestore(alertId)}
                  />
                </Tooltip>
              ]}
            >
              <List.Item.Meta
                title={getAlertName(alertId)}
                description={<span style={{ fontSize: '12px', color: '#999' }}>{alertId}</span>}
              />
            </List.Item>
          )}
        />
      )}
    </Card>
  )
}
