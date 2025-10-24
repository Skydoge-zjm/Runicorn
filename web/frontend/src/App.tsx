import React, { useEffect, useMemo, useState } from 'react'
import { Layout, Menu, Tag, Button, ConfigProvider, theme, Select } from 'antd'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { SettingOutlined, CloudSyncOutlined, ExperimentOutlined, DatabaseOutlined, CloudServerOutlined } from '@ant-design/icons'
import RunDetailPage from './pages/RunDetailPage'
import ExperimentPage from './pages/ExperimentPage'
import ArtifactsPage from './pages/ArtifactsPage'
import ArtifactDetailPage from './pages/ArtifactDetailPage'
import RemoteViewerPage from './pages/RemoteViewerPage'
import { health, getConfig } from './api'
import SettingsDrawer, { UiSettings } from './components/SettingsDrawer'
import { SettingsProvider } from './contexts/SettingsContext'
import { useTranslation } from 'react-i18next'

const { Header, Content, Footer } = Layout

export default function App() {
  const location = useLocation()
  const getSelectedKey = () => {
    if (location.pathname.startsWith('/remote')) return 'remote'
    if (location.pathname.startsWith('/artifacts')) return 'artifacts'
    if (location.pathname.startsWith('/runs/')) return 'experiments'  // Detail page also under experiments
    return 'experiments'  // Default to experiments
  }
  const selected = [getSelectedKey()]
  const { t, i18n} = useTranslation()
  // UI Settings with persistence
  const defaultSettings: UiSettings = {
    // Appearance
    themeMode: 'auto',
    accentColor: '#1677ff',
    density: 'default',
    
    // Layout & Visual Effects
    glass: true,
    backgroundType: 'gradient',
    backgroundImageUrl: '',
    backgroundGradient: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
    backgroundColor: '#0b1220',
    backgroundOpacity: 0.9,
    backgroundBlur: 8,
    
    // Performance & Behavior
    autoRefresh: true,
    refreshInterval: 5,
    animationsEnabled: true,
    enableSounds: false,
    
    // Charts & Data Display
    defaultChartHeight: 320,
    showGridLines: true,
    enableChartAnimations: true,
    maxDataPoints: 1000,
  }
  const [settings, setSettings] = useState<UiSettings>(() => {
    try {
      const raw = localStorage.getItem('ui_settings')
      return raw ? { ...defaultSettings, ...JSON.parse(raw) } : defaultSettings
    } catch { return defaultSettings }
  })
  useEffect(() => {
    try { localStorage.setItem('ui_settings', JSON.stringify(settings)) } catch {}
  }, [settings])

  // System dark follow for themeMode=auto
  const [systemDark, setSystemDark] = useState<boolean>(() => window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
  useEffect(() => {
    if (!window.matchMedia) return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => setSystemDark(e.matches)
    try { mq.addEventListener('change', handler) } catch { mq.addListener(handler) }
    return () => { try { mq.removeEventListener('change', handler) } catch { mq.removeListener(handler) } }
  }, [])

  const isDark = settings.themeMode === 'dark' || (settings.themeMode === 'auto' && systemDark)
  const algorithms = useMemo(() => {
    const arr: any[] = [isDark ? theme.darkAlgorithm : theme.defaultAlgorithm]
    if (settings.density === 'compact') arr.push(theme.compactAlgorithm)
    return arr
  }, [isDark, settings.density])

  const tokenOverrides = useMemo(() => {
    const t: any = { colorPrimary: settings.accentColor }
    if (settings.density === 'loose') {
      t.borderRadius = 10
      t.padding = 16
    }
    return t
  }, [settings.accentColor, settings.density])

  const bgStyle = useMemo<React.CSSProperties>(() => {
    const s: React.CSSProperties = {
      position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
      opacity: settings.backgroundOpacity,
      transition: 'background 0.3s ease',
    }
    if (settings.backgroundType === 'image' && settings.backgroundImageUrl) {
      s.backgroundImage = `url(${settings.backgroundImageUrl})`
      s.backgroundSize = 'cover'
      s.backgroundRepeat = 'no-repeat'
      s.backgroundPosition = 'center center'
    } else if (settings.backgroundType === 'gradient') {
      s.backgroundImage = settings.backgroundGradient
    } else {
      s.background = settings.backgroundColor
    }
    return s
  }, [settings.backgroundType, settings.backgroundImageUrl, settings.backgroundGradient, settings.backgroundColor, settings.backgroundOpacity])

  const wrapperStyle = useMemo<React.CSSProperties>(() => {
    const baseStyle: React.CSSProperties = {
      borderRadius: 8,
      transition: settings.animationsEnabled ? 'all 0.3s ease' : 'none',
    }
    
    if (settings.glass) {
      const bg = isDark ? 'rgba(0,0,0,0.25)' : 'rgba(255,255,255,0.6)'
      return {
        ...baseStyle,
        background: bg,
        backdropFilter: `blur(${settings.backgroundBlur}px)`,
        WebkitBackdropFilter: `blur(${settings.backgroundBlur}px)`,
        boxShadow: isDark ? '0 4px 30px rgba(0,0,0,0.3)' : '0 4px 30px rgba(0,0,0,0.1)'
      }
    }
    return { 
      ...baseStyle,
      background: isDark ? '#111a2c' : '#fff' 
    }
  }, [settings.glass, settings.backgroundBlur, settings.animationsEnabled, isDark])

  const [settingsOpen, setSettingsOpen] = useState(false)

  // First-run: if user_root_dir is empty, automatically open Settings
  useEffect(() => {
    (async () => {
      try {
        const cfg = await getConfig()
        if (!cfg.user_root_dir || cfg.user_root_dir.trim() === '') {
          setSettingsOpen(true)
        }
      } catch {}
    })()
  }, [])

  const [apiStatus, setApiStatus] = useState<'ok' | 'down' | 'loading'>('loading')
  const [failureCount, setFailureCount] = useState(0)
  
  useEffect(() => {
    let active = true
    const ping = async () => {
      try {
        await health()
        if (active) {
          setApiStatus('ok')
          setFailureCount(0) // Reset failure count on success
        }
      } catch {
        if (active) {
          // Only mark as 'down' after 2 consecutive failures to avoid false positives
          setFailureCount(prev => {
            const newCount = prev + 1
            if (newCount >= 2) {
              setApiStatus('down')
            }
            return newCount
          })
        }
      }
    }
    ping()
    // Use user-configured refresh interval (convert to milliseconds)
    const interval = (settings.autoRefresh ? settings.refreshInterval : 5) * 1000
    const t = setInterval(ping, interval)
    return () => { active = false; clearInterval(t) }
  }, [settings.autoRefresh, settings.refreshInterval])

  return (
    <ConfigProvider theme={{ 
      algorithm: algorithms as any, 
      token: {
        ...tokenOverrides,
        motion: settings.animationsEnabled
      }
    }}>
      <SettingsProvider value={{ settings, setSettings }}>
        <div style={bgStyle} />
        <Layout style={{ 
          minHeight: '100vh', 
          position: 'relative', 
          zIndex: 1, 
          background: 'transparent',
          transition: settings.animationsEnabled ? 'all 0.3s ease' : 'none'
        }}>
          <Header style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ color: '#fff', fontWeight: 700, marginRight: 24 }}>{t('app.title')}</div>
            <Menu
              theme="dark"
              mode="horizontal"
              selectedKeys={selected}
              items={[
                { key: 'experiments', icon: <ExperimentOutlined />, label: <Link to="/">{t('menu.experiments')}</Link> },
                { key: 'artifacts', icon: <DatabaseOutlined />, label: <Link to="/artifacts">{t('menu.artifacts')}</Link> },
                { key: 'remote', icon: <CloudServerOutlined />, label: <Link to="/remote">{t('menu.remote')}</Link> },
              ]}
              style={{ flex: 1, minWidth: 0 }}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {apiStatus === 'ok' && <Tag color="green">{t('tag.api_ok')}</Tag>}
              {apiStatus === 'loading' && <Tag color="processing">{t('tag.api_loading')}</Tag>}
              {apiStatus === 'down' && <Tag>{t('tag.api_down')}</Tag>}
              <Select
                size="small"
                value={i18n.language?.startsWith('zh') ? 'zh' : 'en'}
                onChange={(lng) => i18n.changeLanguage(lng)}
                style={{ width: 88 }}
                options={[{ value: 'en', label: 'EN' }, { value: 'zh', label: '中文' }]}
              />
              <Button type="link" icon={<SettingOutlined style={{ color: '#fff' }} />} onClick={() => setSettingsOpen(true)} />
            </div>
          </Header>
          <Content style={{ padding: '24px' }}>
            <div style={{ ...wrapperStyle, padding: 24, minHeight: 360 }}>
              <Routes>
                <Route path="/" element={<ExperimentPage />} />
                <Route path="/runs/:id" element={<RunDetailPage />} />
                <Route path="/artifacts" element={<ArtifactsPage />} />
                <Route path="/artifacts/:name" element={<ArtifactDetailPage />} />
                <Route path="/remote" element={<RemoteViewerPage />} />
              </Routes>
            </div>
          </Content>
          <Footer style={{ textAlign: 'center' }}> {new Date().getFullYear()} {t('app.title')}</Footer>
        </Layout>
        <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} value={settings} onChange={setSettings} />
      </SettingsProvider>
    </ConfigProvider>
  )
}
