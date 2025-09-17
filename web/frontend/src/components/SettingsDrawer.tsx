import React, { useEffect, useState } from 'react'
import { Drawer, Segmented, Radio, Input, Slider, ColorPicker, Space, Typography, Button, Divider, message, Upload } from 'antd'
import { getConfig, setUserRootDir as apiSetUserRootDir, importArchive } from '../api'
import { useTranslation } from 'react-i18next'

export type UiSettings = {
  themeMode: 'light' | 'dark' | 'auto'
  accentColor: string
  density: 'compact' | 'default' | 'loose'
  glass: boolean
  backgroundType: 'image' | 'gradient' | 'color'
  backgroundImageUrl: string
  backgroundGradient: string
  backgroundColor: string
  backgroundOpacity: number
  backgroundBlur: number
}

const gradientPresets: { label: string; value: string }[] = [
  { label: 'Aurora', value: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)' },
  { label: 'Sunset', value: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)' },
  { label: 'Ocean', value: 'linear-gradient(135deg, #5ee7df 0%, #b490ca 100%)' },
  { label: 'Forest', value: 'linear-gradient(135deg, #a8e063 0%, #56ab2f 100%)' },
]

export default function SettingsDrawer({ open, onClose, value, onChange }: {
  open: boolean
  onClose: () => void
  value: UiSettings
  onChange: (v: UiSettings) => void
}) {
  const { t } = useTranslation()
  const set = (patch: Partial<UiSettings>) => onChange({ ...value, ...patch })
  const densityTips = {
    compact: t('settings.appearance.density_compact'),
    default: t('settings.appearance.density_default'),
    loose: t('settings.appearance.density_loose'),
  } as const

  // ----- Data directory (user_root_dir) settings -----
  const [userRootDir, setUserRootDir] = useState<string>('')
  const [storagePath, setStoragePath] = useState<string>('')
  const [savingRoot, setSavingRoot] = useState(false)
  const [importing, setImporting] = useState(false)

  

  

  useEffect(() => {
    let active = true
    if (open) {
      getConfig()
        .then(({ user_root_dir, storage }) => {
          if (!active) return
          setUserRootDir(user_root_dir || '')
          setStoragePath(storage || '')
        })
        .catch(() => {})
    }
    return () => { active = false }
  }, [open])

  const saveUserRoot = async () => {
    if (!userRootDir || userRootDir.trim().length < 2) {
      message.warning(t('settings.messages.enter_valid_path'))
      return
    }
    try {
      setSavingRoot(true)
      const res = await apiSetUserRootDir(userRootDir.trim())
      setStoragePath(res.storage)
      message.success(t('settings.messages.updated'))
    } catch (e: any) {
      message.error(typeof e?.message === 'string' ? e.message : t('settings.messages.update_failed'))
    } finally {
      setSavingRoot(false)
    }
  }

  return (
    <Drawer title={t('settings.drawer.title')} width={520} open={open} onClose={onClose} destroyOnClose>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Typography.Title level={5}>{t('settings.theme.title')}</Typography.Title>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <div style={{ marginBottom: 6 }}>{t('settings.theme.mode')}</div>
              <Radio.Group
                value={value.themeMode}
                onChange={(e) => set({ themeMode: e.target.value })}
                options={[
                  { label: t('settings.theme.light'), value: 'light' },
                  { label: t('settings.theme.dark'), value: 'dark' },
                  { label: t('settings.theme.auto'), value: 'auto' },
                ]}
                optionType="button"
              />
            </div>

        <Divider style={{ margin: '8px 0' }} />

        <div>
          <Typography.Title level={5}>{t('settings.data.title')}</Typography.Title>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div style={{ color: '#999' }}>{t('settings.data.current_storage', { path: storagePath || '-' })}</div>
            <div>{t('settings.data.user_root.label')}</div>
            <Input
              placeholder={t('settings.data.user_root.placeholder')}
              value={userRootDir}
              onChange={(e) => setUserRootDir(e.target.value)}
            />
            <div style={{ fontSize: 12, color: '#999' }}>{t('settings.data.note')}</div>
            <div style={{ textAlign: 'right' }}>
              <Button loading={savingRoot} type="primary" onClick={saveUserRoot}>{t('settings.data.save')}</Button>
            </div>
          </Space>
        </div>
            <div>
              <div style={{ marginBottom: 6 }}>{t('settings.appearance.primary_color')}</div>
              <ColorPicker value={value.accentColor} onChange={(c) => set({ accentColor: c.toHexString() })} />
            </div>
            <div>
              <div style={{ marginBottom: 6 }}>{t('settings.appearance.density')}</div>
              <Segmented
                value={value.density}
                onChange={(v) => set({ density: v as any })}
                options={[
                  { label: densityTips.compact, value: 'compact' },
                  { label: densityTips.default, value: 'default' },
                  { label: densityTips.loose, value: 'loose' },
                ]}
              />
            </div>
            <div>
              <div style={{ marginBottom: 6 }}>{t('settings.glass')}</div>
              <Radio.Group
                value={value.glass}
                onChange={(e) => set({ glass: e.target.value })}
                options={[{ label: t('settings.glass.on'), value: true }, { label: t('settings.glass.off'), value: false }]}
                optionType="button"
              />
            </div>
          </Space>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        <div>
          <Typography.Title level={5}>{t('background.title')}</Typography.Title>
          <div style={{ marginBottom: 8 }}>
            <Segmented
              value={value.backgroundType}
              onChange={(v) => set({ backgroundType: v as any })}
              options={[
                { label: t('background.type.image'), value: 'image' },
                { label: t('background.type.gradient'), value: 'gradient' },
                { label: t('background.type.color'), value: 'color' },
              ]}
            />
          </div>
          {value.backgroundType === 'image' && (
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>{t('background.image_url')}</div>
              <Input
                placeholder="https://... .jpg/.png"
                value={value.backgroundImageUrl}
                onChange={(e) => set({ backgroundImageUrl: e.target.value })}
              />
              {value.backgroundImageUrl && (
                <div style={{ border: '1px solid #eee', borderRadius: 6, overflow: 'hidden' }}>
                  <img src={value.backgroundImageUrl} style={{ width: '100%', display: 'block', maxHeight: 180, objectFit: 'cover' }} />
                </div>
              )}
            </Space>
          )}
          {value.backgroundType === 'gradient' && (
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>{t('background.gradient_presets')}</div>
              <Segmented
                block
                value={value.backgroundGradient}
                onChange={(v) => set({ backgroundGradient: v as string })}
                options={gradientPresets}
              />
            </Space>
          )}
          {value.backgroundType === 'color' && (
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>{t('background.color')}</div>
              <ColorPicker value={value.backgroundColor} onChange={(c) => set({ backgroundColor: c.toHexString() })} />
            </Space>
          )}
          <div style={{ marginTop: 12 }}>{t('background.opacity')}</div>
          <Slider min={0} max={1} step={0.01} value={value.backgroundOpacity} onChange={(v) => set({ backgroundOpacity: Array.isArray(v) ? v[0] : v })} />
          <div>{t('background.blur')}</div>
          <Slider min={0} max={30} step={1} value={value.backgroundBlur} onChange={(v) => set({ backgroundBlur: Array.isArray(v) ? v[0] : v })} />
        </div>

        <Divider style={{ margin: '8px 0' }} />

        <div>
          <Typography.Title level={5}>{t('offline_import.title')}</Typography.Title>
          <Typography.Paragraph type="secondary">
            {t('offline_import.desc')}
          </Typography.Paragraph>
          <Upload.Dragger
            accept=".zip,.tar.gz,.tgz"
            multiple={false}
            showUploadList={false}
            disabled={importing}
            beforeUpload={async (file) => {
              try {
                setImporting(true)
                const res = await importArchive(file as any)
                const added = (res?.new_run_ids || []).length
                message.success(t('offline_import.success', { count: added }))
              } catch (e: any) {
                message.error(typeof e?.message === 'string' ? e.message : t('offline_import.failed'))
              } finally {
                setImporting(false)
              }
              return false
            }}
          >
            <div style={{ padding: 16, textAlign: 'center' }}>
              <div style={{ marginBottom: 8 }}>{t('offline_import.drag')}</div>
              <div style={{ fontSize: 12, color: '#999' }}>{t('offline_import.supports')}</div>
              {importing && <div style={{ marginTop: 8, color: '#1677ff' }}>{t('offline_import.importing')}</div>}
            </div>
          </Upload.Dragger>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        <div>
          <Typography.Title level={5}>{t('remote_moved.title')}</Typography.Title>
          <Typography.Paragraph type="secondary">
            {t('remote_moved.tip')} <a href="/remote">Remote</a>
          </Typography.Paragraph>
        </div>

        <div style={{ textAlign: 'right' }}>
          <Button onClick={onClose} type="primary">{t('settings.done')}</Button>
        </div>
      </Space>
    </Drawer>
  )
}
