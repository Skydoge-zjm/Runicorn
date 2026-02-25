import { useEffect, useMemo, useState } from 'react'
import { Layout, Tag, Button, ConfigProvider, theme, Select } from 'antd'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import enUS from 'antd/locale/en_US'
import zhCN from 'antd/locale/zh_CN'
import { Routes, Route, NavLink } from 'react-router-dom'
import { SettingOutlined, ExperimentOutlined, CloudServerOutlined, DashboardOutlined, AppstoreOutlined } from '@ant-design/icons'
import RunDetailPage from './pages/RunDetailPage'
import ExperimentPage from './pages/ExperimentPage'
import AssetsPage from './pages/AssetsPage'
import AssetDetailPage from './pages/AssetDetailPage'
import RemoteViewerPage from './pages/RemoteViewerPage'
import PerformanceMonitorPage from './pages/PerformanceMonitorPage'
import { PageTransition } from './components/animations/PageTransition'
import { health, getConfig } from './api'
import SettingsDrawer from './components/SettingsDrawer'
import type { UiSettings } from './components/settings/themePresets'
import { SettingsProvider } from './contexts/SettingsContext'
import { GpuTelemetryProvider } from './contexts/GpuTelemetryContext'
import { useTranslation } from 'react-i18next'

const { Content } = Layout

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      refetchOnWindowFocus: true,
      retry: 1,
    },
  },
})

const navItems = [
  { key: 'experiments', path: '/', icon: <ExperimentOutlined />, labelKey: 'menu.experiments' },
  { key: 'assets', path: '/assets', icon: <AppstoreOutlined />, labelKey: 'menu.assets' },
  { key: 'performance', path: '/performance', icon: <DashboardOutlined />, labelKey: 'menu.performance' },
  { key: 'remote', path: '/remote', icon: <CloudServerOutlined />, labelKey: 'menu.remote' },
]

export default function App() {
  const { t, i18n} = useTranslation()
  // UI Settings with persistence
  const defaultSettings: UiSettings = {
    // Appearance
    themeMode: 'auto',
    accentColor: '#1677ff',
    density: 'default',
    
    // Layout & Visual Effects
    glass: false,
    backgroundType: 'color',
    backgroundImageUrl: '',
    backgroundGradient: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
    backgroundColor: '#F0F2F5',
    backgroundColorDark: '#0d0d12',
    surfaceColor: '#ffffff',
    surfaceColorDark: '#1e1e2e',
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
    compareTooltipShowId: false,
    
    // Performance Monitor Tab Settings
    showCpuTab: true,
    showMemoryDiskTab: true,
    showGpuMetricsTab: true,
    showGpuTelemetryTab: true,
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

  // Sync body background with theme so opacity=0 backgrounds still look correct
  useEffect(() => {
    document.documentElement.style.background = isDark ? '#141414' : '#ffffff'
  }, [isDark])
  const algorithms = useMemo(() => {
    const arr: any[] = [isDark ? theme.darkAlgorithm : theme.defaultAlgorithm]
    if (settings.density === 'compact') arr.push(theme.compactAlgorithm)
    return arr
  }, [isDark, settings.density])

  const surfaceBg = isDark ? settings.surfaceColorDark : settings.surfaceColor

  const tokenOverrides = useMemo(() => {
    const tok: any = {
      colorPrimary: settings.accentColor,
      colorBgContainer: isDark ? settings.surfaceColorDark : settings.surfaceColor,
    }
    if (settings.density === 'loose') {
      tok.borderRadius = 10
      tok.padding = 20
      tok.paddingLG = 28
      tok.paddingContentVertical = 16
      tok.paddingContentHorizontal = 24
      tok.marginLG = 28
      tok.fontSize = 15
      tok.fontSizeLG = 18
      tok.controlHeight = 38
      tok.controlHeightLG = 48
      tok.controlHeightSM = 30
    }
    return tok
  }, [settings.accentColor, settings.density, isDark, settings.surfaceColor, settings.surfaceColorDark])

  const bgStyle = useMemo<React.CSSProperties>(() => {
    const s: React.CSSProperties = {
      position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
      opacity: settings.backgroundOpacity,
      transition: 'background 0.3s ease',
    }
    if (settings.backgroundType === 'image' && settings.backgroundImageUrl && /^(https?:\/\/|data:image\/)/.test(settings.backgroundImageUrl)) {
      s.backgroundImage = `url(${CSS.escape(settings.backgroundImageUrl)})`
      s.backgroundSize = 'cover'
      s.backgroundRepeat = 'no-repeat'
      s.backgroundPosition = 'center center'
    } else if (settings.backgroundType === 'gradient') {
      s.backgroundImage = settings.backgroundGradient
    } else {
      s.background = isDark ? settings.backgroundColorDark : settings.backgroundColor
    }
    return s
  }, [settings.backgroundType, settings.backgroundImageUrl, settings.backgroundGradient, settings.backgroundColor, settings.backgroundOpacity, isDark])

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
      background: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.35)',
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
  const [, setFailureCount] = useState(0)
  
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
    const timer = setInterval(ping, interval)
    return () => { active = false; clearInterval(timer) }
  }, [settings.autoRefresh, settings.refreshInterval])

  return (
    <QueryClientProvider client={queryClient}>
    <ConfigProvider
      locale={i18n.language?.startsWith('zh') ? zhCN : enUS}
      theme={{
        algorithm: algorithms as any,
        token: {
          ...tokenOverrides,
          motion: settings.animationsEnabled,
        },
      }}
    >
      <SettingsProvider value={{ settings, setSettings }}>
      <GpuTelemetryProvider>
        <div style={bgStyle} />
        <Layout style={{ 
          height: '100vh',
          overflow: 'hidden',  // Prevent page-level scrolling
          position: 'relative', 
          zIndex: 1, 
          background: 'transparent',
          transition: settings.animationsEnabled ? 'all 0.3s ease' : 'none',
          display: 'flex',
          flexDirection: 'column',
        }}>
          <header style={{
            display: 'flex',
            alignItems: 'center',
            height: 56,
            borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'}`,
            background: surfaceBg,
            padding: '0 20px',
            flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginRight: 24, flexShrink: 0 }}>
              <img
                src="/logo.jpg"
                alt="Runicorn"
                style={{ height: 32, width: 32, borderRadius: 6, objectFit: 'cover' }}
              />
              <span style={{ fontWeight: 700, fontSize: 18, color: isDark ? 'rgba(255,255,255,0.85)' : 'rgba(0,0,0,0.88)', letterSpacing: -0.3 }}>
                {t('app.title')}
              </span>
            </div>
            <div style={{
              width: 1,
              height: 24,
              background: isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.06)',
              marginRight: 20,
              flexShrink: 0,
            }} />
            <nav style={{ display: 'flex', gap: 20, flex: 1 }}>
              {navItems.map(item => (
                <NavLink
                  key={item.key}
                  to={item.path}
                  end={item.path === '/'}
                  style={({ isActive }) => ({
                    color: isActive ? settings.accentColor : (isDark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.45)'),
                    borderBottom: isActive ? `2px solid ${settings.accentColor}` : '2px solid transparent',
                    padding: '16px 0',
                    textDecoration: 'none',
                    fontSize: 14,
                    fontWeight: isActive ? 600 : 400,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                    transition: 'color 0.2s, border-color 0.2s',
                  })}
                >
                  {item.icon} <span className="nav-label">{t(item.labelKey)}</span>
                </NavLink>
              ))}
            </nav>
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
              <Button
                type="text"
                icon={<SettingOutlined style={{ color: isDark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.45)' }} />}
                onClick={() => setSettingsOpen(true)}
                aria-label="Open settings"
              />
            </div>
          </header>
          <Content style={{ 
            flex: 1,
            padding: '16px 24px',
            overflow: 'hidden',  // Content area doesn't scroll
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0,  // Important for flex child
          }}>
            <div style={{ 
              ...wrapperStyle, 
              padding: 0,
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              minHeight: 0,
            }}>
              <PageTransition>
                <Routes>
                  <Route path="/" element={<ExperimentPage />} />
                  <Route path="/runs/:id" element={<RunDetailPage />} />
                  <Route path="/assets" element={<AssetsPage />} />
                  <Route path="/assets/:id" element={<AssetDetailPage />} />
                  <Route path="/performance" element={<PerformanceMonitorPage />} />
                  <Route path="/remote" element={<RemoteViewerPage />} />
                </Routes>
              </PageTransition>
            </div>
          </Content>
        </Layout>
        <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} value={settings} onChange={setSettings} />
      </GpuTelemetryProvider>
      </SettingsProvider>
    </ConfigProvider>
    </QueryClientProvider>
  )
}
