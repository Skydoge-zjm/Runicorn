import React, { useEffect, useState } from 'react'
import { Drawer, Tabs, Segmented, Radio, Input, Slider, ColorPicker, Space, Typography, Button, Divider, message, Upload, Card, Switch, InputNumber, Tooltip, Select, Alert } from 'antd'
import { AppstoreOutlined, BgColorsOutlined, DatabaseOutlined, SettingOutlined, InfoCircleOutlined, ThunderboltOutlined, GlobalOutlined, ExportOutlined } from '@ant-design/icons'
import { getConfig, setUserRootDir as apiSetUserRootDir, importArchive } from '../api'
import { useTranslation } from 'react-i18next'

export type UiSettings = {
  // Appearance
  themeMode: 'light' | 'dark' | 'auto'
  accentColor: string
  density: 'compact' | 'default' | 'loose'
  
  // Layout & Visual Effects
  glass: boolean
  backgroundType: 'image' | 'gradient' | 'color'
  backgroundImageUrl: string
  backgroundGradient: string
  backgroundColor: string
  backgroundOpacity: number
  backgroundBlur: number
  
  // Performance & Behavior
  autoRefresh: boolean
  refreshInterval: number
  animationsEnabled: boolean
  enableSounds: boolean
  
  // Charts & Data Display
  defaultChartHeight: number
  showGridLines: boolean
  enableChartAnimations: boolean
  maxDataPoints: number
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

  const renderAppearanceTab = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small" title={<Space><AppstoreOutlined />{t('settings.cards.theme')}</Space>}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Typography.Text strong>{t('settings.theme.mode')}</Typography.Text>
            <Radio.Group
              value={value.themeMode}
              onChange={(e) => set({ themeMode: e.target.value })}
              options={[
                { label: t('settings.theme.light'), value: 'light' },
                { label: t('settings.theme.dark'), value: 'dark' },
                { label: t('settings.theme.auto'), value: 'auto' },
              ]}
              optionType="button"
              style={{ width: '100%', marginTop: 8 }}
            />
          </div>
          
          <div>
            <Typography.Text strong>{t('settings.appearance.primary_color')}</Typography.Text>
            <div style={{ marginTop: 8 }}>
              <ColorPicker 
                value={value.accentColor} 
                onChange={(c) => set({ accentColor: c.toHexString() })}
                showText
                format="hex"
              />
            </div>
          </div>
          
          <div>
            <Typography.Text strong>{t('settings.appearance.density')}</Typography.Text>
            <Segmented
              value={value.density}
              onChange={(v) => set({ density: v as any })}
              options={[
                { label: t('settings.appearance.density_compact'), value: 'compact' },
                { label: t('settings.appearance.density_default'), value: 'default' },
                { label: t('settings.appearance.density_loose'), value: 'loose' },
              ]}
              style={{ width: '100%', marginTop: 8 }}
            />
          </div>
        </Space>
      </Card>
    </Space>
  )

  const renderLayoutTab = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small" title={<Space><BgColorsOutlined />{t('settings.cards.background')}</Space>}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Typography.Text strong>{t('background.type.label')}</Typography.Text>
            <Segmented
              value={value.backgroundType}
              onChange={(v) => set({ backgroundType: v as any })}
              options={[
                { label: t('background.type.image'), value: 'image' },
                { label: t('background.type.gradient'), value: 'gradient' },
                { label: t('background.type.color'), value: 'color' },
              ]}
              style={{ width: '100%', marginTop: 8 }}
            />
          </div>
          
          {value.backgroundType === 'image' && (
            <div>
              <Typography.Text strong>{t('background.image_url')}</Typography.Text>
              <Input
                placeholder={t('background.image_url.placeholder')}
                value={value.backgroundImageUrl}
                onChange={(e) => set({ backgroundImageUrl: e.target.value })}
                style={{ marginTop: 8 }}
              />
              {value.backgroundImageUrl && (
                <div style={{ border: '1px solid #eee', borderRadius: 6, overflow: 'hidden', marginTop: 8 }}>
                  <img 
                    src={value.backgroundImageUrl} 
                    style={{ width: '100%', display: 'block', maxHeight: 120, objectFit: 'cover' }} 
                    alt={t('background.image_preview')}
                  />
                </div>
              )}
            </div>
          )}
          
          {value.backgroundType === 'gradient' && (
            <div>
              <Typography.Text strong>{t('background.gradient_presets')}</Typography.Text>
              <Segmented
                value={value.backgroundGradient}
                onChange={(v) => set({ backgroundGradient: v as string })}
                options={gradientPresets}
                style={{ width: '100%', marginTop: 8 }}
              />
            </div>
          )}
          
          {value.backgroundType === 'color' && (
            <div>
              <Typography.Text strong>{t('background.color')}</Typography.Text>
              <div style={{ marginTop: 8 }}>
                <ColorPicker 
                  value={value.backgroundColor} 
                  onChange={(c) => set({ backgroundColor: c.toHexString() })}
                  showText
                  format="hex"
                />
              </div>
            </div>
          )}
          
          <div>
            <Typography.Text strong>{t('background.opacity')}</Typography.Text>
            <Slider 
              min={0} 
              max={1} 
              step={0.01} 
              value={value.backgroundOpacity} 
              onChange={(v) => set({ backgroundOpacity: Array.isArray(v) ? v[0] : v })}
              marks={{ 0: '0%', 0.5: '50%', 1: '100%' }}
              style={{ marginTop: 8 }}
            />
          </div>
        </Space>
      </Card>
      
      <Card size="small" title={<Space><ThunderboltOutlined />{t('settings.cards.visual_effects')}</Space>}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Typography.Text strong>{t('settings.glass')}</Typography.Text>
              <div style={{ fontSize: '12px', color: '#999' }}>{t('settings.glass.desc')}</div>
            </div>
            <Switch checked={value.glass} onChange={(checked) => set({ glass: checked })} />
          </div>
          
          {value.glass && (
            <div>
              <Typography.Text strong>{t('background.blur')}</Typography.Text>
              <Slider 
                min={0} 
                max={30} 
                step={1} 
                value={value.backgroundBlur} 
                onChange={(v) => set({ backgroundBlur: Array.isArray(v) ? v[0] : v })}
                marks={{ 0: '0px', 15: '15px', 30: '30px' }}
                style={{ marginTop: 8 }}
              />
            </div>
          )}
          
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Typography.Text strong>{t('settings.performance.animations')}</Typography.Text>
              <div style={{ fontSize: '12px', color: '#999' }}>{t('settings.animations.ui_desc')}</div>
            </div>
            <Switch 
              checked={value.animationsEnabled} 
              onChange={(checked) => set({ animationsEnabled: checked })} 
            />
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Typography.Text strong>{t('settings.performance.chart_animations')}</Typography.Text>
              <div style={{ fontSize: '12px', color: '#999' }}>{t('settings.animations.chart_desc')}</div>
            </div>
            <Switch 
              checked={value.enableChartAnimations} 
              onChange={(checked) => set({ enableChartAnimations: checked })} 
            />
          </div>
        </Space>
      </Card>
    </Space>
  )

  const renderDataTab = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small" title={<Space><DatabaseOutlined />{t('settings.cards.storage')}</Space>}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Alert 
            type="info" 
            message={t('settings.data.current_storage', { path: storagePath || t('settings.data.not_configured') || 'Not configured' })}
            style={{ marginBottom: 12 }}
          />
          
          <div>
            <Typography.Text strong>{t('settings.data.user_root.label')}</Typography.Text>
            <Input
              placeholder={t('settings.data.user_root.placeholder')}
              value={userRootDir}
              onChange={(e) => setUserRootDir(e.target.value)}
              style={{ marginTop: 8 }}
            />
            <Typography.Paragraph type="secondary" style={{ fontSize: '12px', margin: '4px 0 8px 0' }}>
              {t('settings.data.note')}
            </Typography.Paragraph>
            <Button 
              loading={savingRoot} 
              type="primary" 
              onClick={saveUserRoot}
              block
            >
              {t('settings.data.save')}
            </Button>
          </div>
        </Space>
      </Card>
      
      <Card size="small" title={<Space><ExportOutlined />{t('settings.cards.import_export')}</Space>}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Typography.Text strong>{t('offline_import.title')}</Typography.Text>
            <Typography.Paragraph type="secondary" style={{ fontSize: '12px', margin: '4px 0' }}>
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
              style={{ padding: '12px' }}
            >
              <div style={{ padding: '8px', textAlign: 'center' }}>
                <div style={{ marginBottom: 4, fontSize: '14px' }}>{t('offline_import.drag')}</div>
                <div style={{ fontSize: '11px', color: '#999' }}>{t('offline_import.supports')}</div>
                {importing && <div style={{ marginTop: 4, color: '#1677ff', fontSize: '12px' }}>{t('offline_import.importing')}</div>}
              </div>
            </Upload.Dragger>
          </div>
        </Space>
      </Card>
    </Space>
  )

  const renderPerformanceTab = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small" title={<Space><ThunderboltOutlined />{t('settings.cards.performance')}</Space>}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Typography.Text strong>{t('settings.performance.auto_refresh')}</Typography.Text>
              <div style={{ fontSize: '12px', color: '#999' }}>{t('settings.auto_refresh.desc')}</div>
            </div>
            <Switch 
              checked={value.autoRefresh} 
              onChange={(checked) => set({ autoRefresh: checked })} 
            />
          </div>
          
          {value.autoRefresh && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
                <Typography.Text strong>{t('settings.performance.refresh_interval')}</Typography.Text>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <InputNumber
                    min={1}
                    max={60}
                    value={value.refreshInterval}
                    onChange={(v) => set({ refreshInterval: v || 5 })}
                    style={{ width: 80 }}
                  />
                  <span style={{ fontSize: '12px', color: '#999' }}>{t('settings.units.seconds')}</span>
                </div>
              </div>
            </div>
          )}
          
          <div>
            <Typography.Text strong>{t('settings.charts.default_height')}</Typography.Text>
            <Slider
              min={200}
              max={600}
              step={20}
              value={value.defaultChartHeight}
              onChange={(v) => set({ defaultChartHeight: Array.isArray(v) ? v[0] : v })}
              marks={{ 200: '200px', 300: '300px', 400: '400px', 600: '600px' }}
              style={{ marginTop: 8 }}
            />
          </div>
          
          <div>
            <div style={{ marginTop: 8 }}>
              <Typography.Text strong>{t('settings.charts.max_points')}</Typography.Text>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
                <InputNumber
                  min={100}
                  max={10000}
                  step={100}
                  value={value.maxDataPoints}
                  onChange={(v) => set({ maxDataPoints: v || 1000 })}
                  style={{ width: 120 }}
                />
                <span style={{ fontSize: '12px', color: '#999' }}>{t('settings.units.points')}</span>
              </div>
            </div>
          </div>
        </Space>
      </Card>
      
      <Card size="small" title={<Space><GlobalOutlined />{t('settings.cards.advanced')}</Space>}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Typography.Text strong>{t('settings.charts.grid_lines')}</Typography.Text>
              <div style={{ fontSize: '12px', color: '#999' }}>{t('settings.grid_lines.desc')}</div>
            </div>
            <Switch 
              checked={value.showGridLines} 
              onChange={(checked) => set({ showGridLines: checked })} 
            />
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Typography.Text strong>{t('settings.performance.sounds')}</Typography.Text>
              <div style={{ fontSize: '12px', color: '#999' }}>{t('settings.sounds.desc')}</div>
            </div>
            <Switch 
              checked={value.enableSounds} 
              onChange={(checked) => set({ enableSounds: checked })} 
            />
          </div>
        </Space>
      </Card>
    </Space>
  )

  return (
    <Drawer 
      title={
        <Space>
          <SettingOutlined />
          <span style={{ fontSize: '16px', fontWeight: 600 }}>{t('settings.drawer.title')}</span>
        </Space>
      } 
      width={600} 
      open={open} 
      onClose={onClose} 
      destroyOnClose
      styles={{
        body: { padding: '16px' }
      }}
    >
      <Tabs
        defaultActiveKey="appearance"
        items={[
          {
            key: 'appearance',
            label: (
              <Space>
                <AppstoreOutlined />
                <span>{t('settings.tabs.appearance')}</span>
              </Space>
            ),
            children: renderAppearanceTab(),
          },
          {
            key: 'layout',
            label: (
              <Space>
                <BgColorsOutlined />
                <span>{t('settings.tabs.layout')}</span>
              </Space>
            ),
            children: renderLayoutTab(),
          },
          {
            key: 'data',
            label: (
              <Space>
                <DatabaseOutlined />
                <span>{t('settings.tabs.data')}</span>
              </Space>
            ),
            children: renderDataTab(),
          },
          {
            key: 'performance',
            label: (
              <Space>
                <ThunderboltOutlined />
                <span>{t('settings.tabs.performance')}</span>
              </Space>
            ),
            children: renderPerformanceTab(),
          },
        ]}
        tabPosition="top"
        size="small"
        style={{ height: 'calc(100vh - 120px)' }}
      />
      
      <div style={{ 
        position: 'absolute', 
        bottom: 16, 
        right: 16, 
        left: 16,
        borderTop: '1px solid #f0f0f0',
        paddingTop: 16,
        background: 'rgba(255, 255, 255, 0.9)',
        backdropFilter: 'blur(8px)'
      }}>
        <Button onClick={onClose} type="primary" size="large" block>
          {t('settings.done')}
        </Button>
      </div>
    </Drawer>
  )
}
