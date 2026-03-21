import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Drawer, Tabs, Segmented, Radio, Input, Slider, ColorPicker, Space, Typography, Button, Divider, App, Upload, Card, Switch, InputNumber, Alert, Modal, Tag, Select, theme } from 'antd'
import { WarningOutlined, SearchOutlined, FolderOpenOutlined } from '@ant-design/icons'
import { AppstoreOutlined, BgColorsOutlined, DatabaseOutlined, SettingOutlined, InfoCircleOutlined, ThunderboltOutlined, EyeOutlined, ExportOutlined, BellOutlined, DashboardOutlined } from '@ant-design/icons'
import { getConfig, setUserRootDir as apiSetUserRootDir, previewImport, confirmImport, listLocalStorageCandidates } from '../api'
import type { ImportPreviewResult } from '../api'
import type { RemoteStorageCandidate } from '../types/remote'
import { useTranslation } from 'react-i18next'
import SystemInfoPanel from './SystemInfoPanel'
import DismissedAlertsManager from './DismissedAlertsManager'
import GpuCollectorSettings from './settings/GpuCollectorSettings'
import { gradientPresets, themePresets, detectActivePreset } from './settings/themePresets'
import type { UiSettings } from './settings/themePresets'

// Re-export so existing consumers (App.tsx, SettingsContext.tsx) don't need to change imports
export type { UiSettings }

export default function SettingsDrawer({ open, onClose, value, onChange }: {
  open: boolean
  onClose: () => void
  value: UiSettings
  onChange: (v: UiSettings) => void
}) {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const set = (patch: Partial<UiSettings>) => onChange({ ...value, ...patch })
  const [appearanceSub, setAppearanceSub] = useState<'theme' | 'visibility' | 'alerts'>('theme')
  // ----- Data directory
  const [userRootDir, setUserRootDir] = useState<string>('')
  const [storagePath, setStoragePath] = useState<string>('')
  const [scanRoot, setScanRoot] = useState<string>('')
  const [scanDepth, setScanDepth] = useState<number>(3)
  const [storageCandidates, setStorageCandidates] = useState<RemoteStorageCandidate[]>([])
  const [detectingStorageCandidates, setDetectingStorageCandidates] = useState(false)
  const [storageCandidatesRequested, setStorageCandidatesRequested] = useState(false)
  const [savingRoot, setSavingRoot] = useState(false)
  const [importing, setImporting] = useState(false)
  const [previewData, setPreviewData] = useState<ImportPreviewResult | null>(null)
  const [importMode, setImportMode] = useState<'merge' | 'isolate'>('merge')
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    let active = true
    if (open) {
      getConfig()
        .then(({ user_root_dir, storage, home_directory }) => {
          if (!active) return
          setUserRootDir(user_root_dir || '')
          setStoragePath(storage || '')
          setScanRoot(user_root_dir || home_directory || '')
          setStorageCandidates([])
          setStorageCandidatesRequested(false)
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

  const detectLocalStorageCandidates = async () => {
    if (!scanRoot || scanRoot.trim().length < 1) {
      message.warning(t('settings.messages.enter_valid_path'))
      return
    }

    try {
      setDetectingStorageCandidates(true)
      setStorageCandidatesRequested(true)
      const candidates = await listLocalStorageCandidates(scanRoot.trim(), scanDepth)
      setStorageCandidates(candidates)
    } catch (e: any) {
      setStorageCandidates([])
      message.error(typeof e?.message === 'string' ? e.message : t('settings.messages.detect_failed'))
    } finally {
      setDetectingStorageCandidates(false)
    }
  }

  const renderAppearanceTab = () => (
    <div>
      <Segmented
        block
        value={appearanceSub}
        onChange={(v) => setAppearanceSub(v as any)}
        options={[
          { label: t('settings.appearance.sub_theme'), value: 'theme' },
          { label: t('settings.appearance.sub_visibility'), value: 'visibility' },
          { label: t('settings.appearance.sub_alerts'), value: 'alerts' },
        ]}
        style={{ marginBottom: 12 }}
      />

      {appearanceSub === 'theme' && (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Typography.Text strong>{t('settings.preset.label')}</Typography.Text>
            <Select
              value={detectActivePreset(value)}
              onChange={(key) => {
                const preset = themePresets.find(p => p.key === key)
                if (preset) set(preset.settings)
              }}
              placeholder={t('settings.preset.custom')}
              style={{ width: '100%', marginTop: 8 }}
              options={themePresets.map(p => ({
                label: (
                  <Space size={8}>
                    <span style={{
                      display: 'inline-block', width: 14, height: 14, borderRadius: 7,
                      background: `linear-gradient(135deg, ${p.swatch[0]} 0%, ${p.swatch[1]} 100%)`,
                      border: `1px solid ${token.colorBorderSecondary}`,
                      verticalAlign: 'middle',
                    }} />
                    {t(p.labelKey)}
                  </Space>
                ),
                value: p.key,
              }))}
            />
          </div>
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
                <Typography.Text strong>{t('settings.surface_color')}</Typography.Text>
                {value.themeMode === 'auto' ? (
                  <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
                    <div>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('settings.theme.light')}</Typography.Text>
                      <div style={{ marginTop: 4 }}>
                        <ColorPicker 
                          value={value.surfaceColor} 
                          onChange={(c) => set({ surfaceColor: c.toHexString() })}
                          showText
                          format="hex"
                        />
                      </div>
                    </div>
                    <div>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('settings.theme.dark')}</Typography.Text>
                      <div style={{ marginTop: 4 }}>
                        <ColorPicker 
                          value={value.surfaceColorDark} 
                          onChange={(c) => set({ surfaceColorDark: c.toHexString() })}
                          showText
                          format="hex"
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div style={{ marginTop: 8 }}>
                    <ColorPicker 
                      value={value.themeMode === 'dark' ? value.surfaceColorDark : value.surfaceColor} 
                      onChange={(c) => set(value.themeMode === 'dark' ? { surfaceColorDark: c.toHexString() } : { surfaceColor: c.toHexString() })}
                      showText
                      format="hex"
                    />
                  </div>
                )}
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
                  {value.themeMode === 'auto' ? (
                    <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
                      <div>
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('settings.theme.light')}</Typography.Text>
                        <div style={{ marginTop: 4 }}>
                          <ColorPicker 
                            value={value.backgroundColor} 
                            onChange={(c) => set({ backgroundColor: c.toHexString() })}
                            showText
                            format="hex"
                          />
                        </div>
                      </div>
                      <div>
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('settings.theme.dark')}</Typography.Text>
                        <div style={{ marginTop: 4 }}>
                          <ColorPicker 
                            value={value.backgroundColorDark} 
                            onChange={(c) => set({ backgroundColorDark: c.toHexString() })}
                            showText
                            format="hex"
                          />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div style={{ marginTop: 8 }}>
                      <ColorPicker 
                        value={value.themeMode === 'dark' ? value.backgroundColorDark : value.backgroundColor} 
                        onChange={(c) => set(value.themeMode === 'dark' ? { backgroundColorDark: c.toHexString() } : { backgroundColor: c.toHexString() })}
                        showText
                        format="hex"
                      />
                    </div>
                  )}
                </div>
              )}
              <div>
                <Typography.Text strong>{t('background.opacity')}</Typography.Text>
                <Slider 
                  min={0} max={1} step={0.01}
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
                  <div style={{ fontSize: '12px', color: token.colorTextSecondary }}>{t('settings.glass.desc')}</div>
                </div>
                <Switch checked={value.glass} onChange={(checked) => set({ glass: checked })} />
              </div>
              {value.glass && (
                <div>
                  <Typography.Text strong>{t('background.blur')}</Typography.Text>
                  <Slider 
                    min={0} max={30} step={1}
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
                  <div style={{ fontSize: '12px', color: token.colorTextSecondary }}>{t('settings.animations.ui_desc')}</div>
                </div>
                <Switch checked={value.animationsEnabled} onChange={(checked) => set({ animationsEnabled: checked })} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Typography.Text strong>{t('settings.performance.chart_animations')}</Typography.Text>
                  <div style={{ fontSize: '12px', color: token.colorTextSecondary }}>{t('settings.animations.chart_desc')}</div>
                </div>
                <Switch checked={value.enableChartAnimations} onChange={(checked) => set({ enableChartAnimations: checked })} />
              </div>
            </Space>
          </Card>
        </Space>
      )}

      {appearanceSub === 'visibility' && (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Card size="small" title={<Space><EyeOutlined />{t('settings.cards.visibility')}</Space>}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Typography.Text strong>{t('settings.charts.default_height')}</Typography.Text>
                <Slider
                  min={200} max={600} step={20}
                  value={value.defaultChartHeight}
                  onChange={(v) => set({ defaultChartHeight: Array.isArray(v) ? v[0] : v })}
                  marks={{ 200: '200px', 300: '300px', 400: '400px', 600: '600px' }}
                  style={{ marginTop: 8 }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Typography.Text strong>{t('settings.charts.grid_lines')}</Typography.Text>
                  <div style={{ fontSize: '12px', color: token.colorTextSecondary }}>{t('settings.grid_lines.desc')}</div>
                </div>
                <Switch checked={value.showGridLines} onChange={(checked) => set({ showGridLines: checked })} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Typography.Text strong>{t('settings.charts.compare_tooltip_id')}</Typography.Text>
                  <div style={{ fontSize: '12px', color: token.colorTextSecondary }}>{t('settings.charts.compare_tooltip_id_desc')}</div>
                </div>
                <Switch checked={value.compareTooltipShowId} onChange={(checked) => set({ compareTooltipShowId: checked })} />
              </div>
              <Divider style={{ margin: '8px 0' }} />
              <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>
                {t('settings.performance.tabs_title')}
              </Typography.Text>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography.Text>{t('settings.performance.show_cpu_tab')}</Typography.Text>
                  <Switch checked={value.showCpuTab} onChange={(checked) => set({ showCpuTab: checked })} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography.Text>{t('settings.performance.show_memory_disk_tab')}</Typography.Text>
                  <Switch checked={value.showMemoryDiskTab} onChange={(checked) => set({ showMemoryDiskTab: checked })} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography.Text>{t('settings.performance.show_gpu_metrics_tab')}</Typography.Text>
                  <Switch checked={value.showGpuMetricsTab} onChange={(checked) => set({ showGpuMetricsTab: checked })} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography.Text>{t('settings.performance.show_gpu_telemetry_tab')}</Typography.Text>
                  <Switch checked={value.showGpuTelemetryTab} onChange={(checked) => set({ showGpuTelemetryTab: checked })} />
                </div>
              </Space>
            </Space>
          </Card>
        </Space>
      )}

      {appearanceSub === 'alerts' && (
        <DismissedAlertsManager />
      )}
    </div>
  )

  const renderStorageTab = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small" title={<Space><DatabaseOutlined />{t('settings.cards.storage')}</Space>}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Alert 
            type="info" 
            message={t('settings.data.current_storage', { path: storagePath || t('settings.data.not_configured') })}
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

          <Divider style={{ margin: '8px 0' }} />

          <div>
            <Typography.Text strong>{t('settings.data.detected_roots.title')}</Typography.Text>
            <Typography.Paragraph type="secondary" style={{ fontSize: '12px', margin: '4px 0 8px 0' }}>
              {t('settings.data.detected_roots.hint')}
            </Typography.Paragraph>
            <Space.Compact style={{ width: '100%', marginBottom: 8 }}>
              <Input
                placeholder={t('settings.data.detected_roots.scan_root_placeholder')}
                value={scanRoot}
                onChange={(e) => setScanRoot(e.target.value)}
              />
              <InputNumber
                min={1}
                max={8}
                value={scanDepth}
                onChange={(v) => setScanDepth(Number(v) || 3)}
                addonBefore={t('settings.data.detected_roots.depth')}
                style={{ width: 130 }}
              />
            </Space.Compact>
            <Button
              icon={<SearchOutlined />}
              loading={detectingStorageCandidates}
              onClick={() => void detectLocalStorageCandidates()}
              style={{ marginBottom: 12 }}
            >
              {t('settings.data.detected_roots.action')}
            </Button>

            {storageCandidates.length > 0 ? (
              <Space direction="vertical" style={{ width: '100%' }} size={8}>
                {storageCandidates.map((candidate) => (
                  <Button
                    key={candidate.path}
                    block
                    icon={<FolderOpenOutlined />}
                    onClick={() => setUserRootDir(candidate.path)}
                    style={{ height: 'auto', justifyContent: 'space-between', paddingBlock: 10 }}
                  >
                    <Space direction="vertical" size={6} style={{ width: '100%', alignItems: 'flex-start' }}>
                      <Typography.Text style={{ wordBreak: 'break-all', textAlign: 'left' }}>
                        {candidate.path}
                      </Typography.Text>
                      <Space size={[6, 6]} wrap>
                        <Tag color="blue">{t('settings.data.detected_roots.candidate_runs', { count: candidate.runCount })}</Tag>
                        {candidate.hasArchive && <Tag color="green">{t('settings.data.detected_roots.candidate_archive')}</Tag>}
                        {candidate.hasIndex && <Tag color="purple">{t('settings.data.detected_roots.candidate_index')}</Tag>}
                      </Space>
                    </Space>
                  </Button>
                ))}
              </Space>
            ) : storageCandidatesRequested ? (
              <Typography.Text type="secondary">
                {t('settings.data.detected_roots.empty')}
              </Typography.Text>
            ) : (
              <Typography.Text type="secondary">
                {t('settings.data.detected_roots.prompt')}
              </Typography.Text>
            )}
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
                  const preview = await previewImport(file as any)
                  setPreviewData(preview)
setImportMode('merge')
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
                <div style={{ fontSize: '11px', color: token.colorTextSecondary }}>{t('offline_import.supports')}</div>
                {importing && <div style={{ marginTop: 4, color: token.colorPrimary, fontSize: '12px' }}>{t('offline_import.previewing')}</div>}
              </div>
            </Upload.Dragger>

            <Modal
              title={t('offline_import.preview_title')}
              open={!!previewData}
              onCancel={() => setPreviewData(null)}
              confirmLoading={confirming}
              onOk={async () => {
                if (!previewData) return
                setConfirming(true)
                try {
                  const res = await confirmImport(previewData.token, importMode)
                  const added = (res?.new_run_ids || []).length
                  const skipped = res?.skipped_count || 0
                  message.success(t(
                    skipped > 0 ? 'offline_import.success_with_skip' : 'offline_import.success',
                    { count: added, skipped },
                  ))
                  setPreviewData(null)
                  // Refresh runs list and assets index so main page shows new data
                  queryClient.invalidateQueries({ queryKey: ['runs'] })
                } catch (e: any) {
                  message.error(typeof e?.message === 'string' ? e.message : t('offline_import.failed'))
                } finally {
                  setConfirming(false)
                }
              }}
              okText={t('offline_import.confirm_import')}
              cancelText={t('experiments.cancel')}
              width={520}
            >
              {previewData && (
                <div>
                  <div style={{ marginBottom: 12 }}>
                    <Typography.Text strong>{t('offline_import.file_label')}</Typography.Text>
                    <Typography.Text style={{ marginLeft: 8 }}>{previewData.filename}</Typography.Text>
                  </div>

                  <div style={{ marginBottom: 12 }}>
                    <Typography.Text strong>
                      {t('offline_import.detected_runs', { count: previewData.total_runs, files: previewData.total_files })}
                    </Typography.Text>
                  </div>

                  <div style={{ maxHeight: 200, overflow: 'auto', marginBottom: 12, border: `1px solid ${token.colorBorderSecondary}`, borderRadius: 6, padding: 8 }}>
                    {previewData.runs.map((r) => (
                      <div key={r.run_id} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 0', fontSize: 12 }}>
                        <code style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {r.path ? `${r.path}/` : ''}{r.run_id}
                        </code>
                        <span style={{ color: token.colorTextSecondary, flexShrink: 0 }}>{r.files_count} files</span>
                        {r.conflict && <Tag color="warning" style={{ marginRight: 0, fontSize: 11 }}>{t('offline_import.conflict')}</Tag>}
                      </div>
                    ))}
                  </div>

                  {previewData.conflict_count > 0 && (
                    <Alert
                      type="warning"
                      icon={<WarningOutlined />}
                      showIcon
                      message={t('offline_import.conflict_warning', { count: previewData.conflict_count })}
                      style={{ marginBottom: 12 }}
                    />
                  )}

                  <div>
                    <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>
                      {t('offline_import.mode_label')}
                    </Typography.Text>
                    <Radio.Group value={importMode} onChange={(e) => setImportMode(e.target.value)}>
                      <Space direction="vertical">
                        <Radio value="isolate">
                          <div>
                            <div style={{ fontWeight: 500 }}>{t('offline_import.mode_isolate')}</div>
                            <div style={{ fontSize: 11, color: token.colorTextSecondary }}>{t('offline_import.mode_isolate_desc')}</div>
                          </div>
                        </Radio>
                        <Radio value="merge">
                          <div>
                            <div style={{ fontWeight: 500 }}>{t('offline_import.mode_merge')}</div>
                            <div style={{ fontSize: 11, color: token.colorTextSecondary }}>{t('offline_import.mode_merge_desc')}</div>
                          </div>
                        </Radio>
                      </Space>
                    </Radio.Group>
                  </div>
                </div>
              )}
            </Modal>
          </div>
        </Space>
      </Card>
    </Space>
  )

  const renderPerformanceTab = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small" title={<Space><ThunderboltOutlined />{t('settings.cards.experiment_refresh')}</Space>}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Typography.Text strong>{t('settings.performance.auto_refresh')}</Typography.Text>
              <div style={{ fontSize: '12px', color: token.colorTextSecondary }}>{t('settings.auto_refresh.desc')}</div>
            </div>
            <Switch 
              checked={value.autoRefresh} 
              onChange={(checked) => set({ autoRefresh: checked })} 
            />
          </div>
          
          {value.autoRefresh && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Typography.Text>{t('settings.performance.refresh_interval')}</Typography.Text>
              <InputNumber
                min={1}
                max={60}
                value={value.refreshInterval}
                onChange={(v) => set({ refreshInterval: v || 5 })}
                style={{ width: 80 }}
              />
              <span style={{ fontSize: 12, color: token.colorTextSecondary }}>{t('settings.units.seconds')}</span>
            </div>
          )}
          
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Typography.Text>{t('settings.charts.max_points')}</Typography.Text>
            <InputNumber
              min={100}
              max={10000}
              step={100}
              value={value.maxDataPoints}
              onChange={(v) => set({ maxDataPoints: v || 1000 })}
              style={{ width: 80 }}
            />
            <span style={{ fontSize: 12, color: token.colorTextSecondary }}>{t('settings.units.points')}</span>
          </div>
        </Space>
      </Card>
      
      <Card size="small" title={<Space><DashboardOutlined />{t('settings.cards.gpu_telemetry')}</Space>}>
        <GpuCollectorSettings />
      </Card>
      
      <Card size="small" title={<Space><BellOutlined />{t('settings.cards.notifications')}</Space>}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Typography.Text strong>{t('settings.performance.sounds')}</Typography.Text>
            <div style={{ fontSize: '12px', color: token.colorTextSecondary }}>{t('settings.sounds.desc')}</div>
          </div>
          <Switch 
            checked={value.enableSounds} 
            onChange={(checked) => set({ enableSounds: checked })} 
          />
        </div>
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
        body: { padding: '16px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }
      }}
    >
      <Tabs
        className="settings-drawer-tabs"
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
            key: 'storage',
            label: (
              <Space>
                <DatabaseOutlined />
                <span>{t('settings.tabs.storage')}</span>
              </Space>
            ),
            children: renderStorageTab(),
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
          {
            key: 'system_info',
            label: (
              <Space>
                <InfoCircleOutlined />
                <span>{t('settings.tabs.system_info')}</span>
              </Space>
            ),
            children: <SystemInfoPanel onOpenDiagnostics={onClose} />,
          },
        ]}
        tabPosition="top"
        size="small"
      />
    </Drawer>
  )
}
