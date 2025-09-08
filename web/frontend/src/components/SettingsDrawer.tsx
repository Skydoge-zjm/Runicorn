import React, { useEffect, useState } from 'react'
import { Drawer, Form, Segmented, Radio, Input, Slider, ColorPicker, Space, Typography, Button, Divider, message } from 'antd'
import { getConfig, setUserRootDir as apiSetUserRootDir } from '../api'

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
  const set = (patch: Partial<UiSettings>) => onChange({ ...value, ...patch })
  const densityTips = {
    compact: '紧凑型（信息密度高）',
    default: '默认',
    loose: '宽松型（更舒适的留白）',
  } as const

  // ----- Data directory (user_root_dir) settings -----
  const [userRootDir, setUserRootDir] = useState<string>('')
  const [storagePath, setStoragePath] = useState<string>('')
  const [savingRoot, setSavingRoot] = useState(false)

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
      message.warning('请输入有效的目录绝对路径（例如 D:\\RunicornData）')
      return
    }
    try {
      setSavingRoot(true)
      const res = await apiSetUserRootDir(userRootDir.trim())
      setStoragePath(res.storage)
      message.success('用户根目录已更新')
    } catch (e: any) {
      message.error(typeof e?.message === 'string' ? e.message : '更新失败')
    } finally {
      setSavingRoot(false)
    }
  }

  return (
    <Drawer title="设置" width={520} open={open} onClose={onClose} destroyOnClose>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Typography.Title level={5}>主题</Typography.Title>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <div style={{ marginBottom: 6 }}>模式</div>
              <Radio.Group
                value={value.themeMode}
                onChange={(e) => set({ themeMode: e.target.value })}
                options={[
                  { label: '浅色', value: 'light' },
                  { label: '深色', value: 'dark' },
                  { label: '跟随系统', value: 'auto' },
                ]}
                optionType="button"
              />
            </div>

        <Divider style={{ margin: '8px 0' }} />

        <div>
          <Typography.Title level={5}>数据目录</Typography.Title>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div style={{ color: '#999' }}>当前存储根（storage）：{storagePath || '未知'}</div>
            <div>用户根目录（优先级低于环境变量 RUNICORN_DIR）</div>
            <Input
              placeholder="例如：D:\\RunicornData"
              value={userRootDir}
              onChange={(e) => setUserRootDir(e.target.value)}
            />
            <div style={{ fontSize: 12, color: '#999' }}>
              设置后将写入用户配置，并立即生效。若设置了环境变量 RUNICORN_DIR，则优先使用环境变量。
            </div>
            <div style={{ textAlign: 'right' }}>
              <Button loading={savingRoot} type="primary" onClick={saveUserRoot}>保存数据目录</Button>
            </div>
          </Space>
        </div>
            <div>
              <div style={{ marginBottom: 6 }}>主色</div>
              <ColorPicker value={value.accentColor} onChange={(c) => set({ accentColor: c.toHexString() })} />
            </div>
            <div>
              <div style={{ marginBottom: 6 }}>密度</div>
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
              <div style={{ marginBottom: 6 }}>玻璃效果</div>
              <Radio.Group
                value={value.glass}
                onChange={(e) => set({ glass: e.target.value })}
                options={[{ label: '开启', value: true }, { label: '关闭', value: false }]}
                optionType="button"
              />
            </div>
          </Space>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        <div>
          <Typography.Title level={5}>背景</Typography.Title>
          <div style={{ marginBottom: 8 }}>
            <Segmented
              value={value.backgroundType}
              onChange={(v) => set({ backgroundType: v as any })}
              options={[
                { label: '图片', value: 'image' },
                { label: '渐变', value: 'gradient' },
                { label: '纯色', value: 'color' },
              ]}
            />
          </div>
          {value.backgroundType === 'image' && (
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>图片地址（URL）</div>
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
              <div>渐变预设</div>
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
              <div>背景颜色</div>
              <ColorPicker value={value.backgroundColor} onChange={(c) => set({ backgroundColor: c.toHexString() })} />
            </Space>
          )}
          <div style={{ marginTop: 12 }}>不透明度</div>
          <Slider min={0} max={1} step={0.01} value={value.backgroundOpacity} onChange={(v) => set({ backgroundOpacity: Array.isArray(v) ? v[0] : v })} />
          <div>模糊强度</div>
          <Slider min={0} max={30} step={1} value={value.backgroundBlur} onChange={(v) => set({ backgroundBlur: Array.isArray(v) ? v[0] : v })} />
        </div>

        <div style={{ textAlign: 'right' }}>
          <Button onClick={onClose} type="primary">完成</Button>
        </div>
      </Space>
    </Drawer>
  )
}
