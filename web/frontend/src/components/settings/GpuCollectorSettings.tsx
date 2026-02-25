/**
 * GPU Collector Settings
 *
 * Server-side GPU background collection controls (enable, interval, max duration).
 * Fully self-contained — manages its own state and API calls.
 */

import { useEffect, useState } from 'react'
import { Space, Typography, Switch, InputNumber, message, theme } from 'antd'
import { useTranslation } from 'react-i18next'
import { getGpuTelemetryConfig, setGpuTelemetryConfig, type GpuCollectorConfig } from '../../api'

export default function GpuCollectorSettings() {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const [cfg, setCfg] = useState<GpuCollectorConfig | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let active = true
    getGpuTelemetryConfig()
      .then(r => { if (active) setCfg(r) })
      .catch(() => {})
    return () => { active = false }
  }, [])

  const update = async (patch: Partial<GpuCollectorConfig>) => {
    setSaving(true)
    try {
      const res = await setGpuTelemetryConfig(patch)
      setCfg({ enabled: res.enabled, interval_sec: res.interval_sec, max_duration_h: res.max_duration_h })
      message.info(t('settings.performance.gpu_collect_restart_hint'))
    } catch {}
    setSaving(false)
  }

  if (!cfg) return null
  return (
    <Space direction="vertical" style={{ width: '100%' }} size={8}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Text strong>{t('settings.performance.gpu_background_collect', 'GPU Background Collection')}</Typography.Text>
        <Switch checked={cfg.enabled} onChange={v => update({ enabled: v })} loading={saving} />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Typography.Text>{t('settings.performance.gpu_poll_interval', 'Poll Interval')}</Typography.Text>
        <InputNumber
          min={1} max={10} step={1}
          value={cfg.interval_sec}
          onChange={v => v != null && update({ interval_sec: v })}
          style={{ width: 80 }}
          disabled={saving}
        />
        <span style={{ fontSize: 12, color: token.colorTextSecondary }}>{t('settings.units.seconds', 's')}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Typography.Text>{t('settings.performance.gpu_max_duration', 'Max History')}</Typography.Text>
        <InputNumber
          min={1} max={24} step={1}
          value={cfg.max_duration_h}
          onChange={v => v != null && update({ max_duration_h: v })}
          style={{ width: 80 }}
          disabled={saving}
        />
        <span style={{ fontSize: 12, color: token.colorTextSecondary }}>{t('settings.units.hours', 'h')}</span>
      </div>
    </Space>
  )
}
