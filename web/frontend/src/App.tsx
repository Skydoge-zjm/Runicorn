import React, { useEffect, useMemo, useState } from 'react'
import { Layout, Menu, Tag, Button, ConfigProvider, theme } from 'antd'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { UnorderedListOutlined, SettingOutlined } from '@ant-design/icons'
import RunsPage from './pages/RunsPage'
import RunDetailPage from './pages/RunDetailPage'
import { health } from './api'
import SettingsDrawer, { UiSettings } from './components/SettingsDrawer'

const { Header, Content, Footer } = Layout

export default function App() {
  const location = useLocation()
  const selected = ['runs']
  // UI Settings with persistence
  const defaultSettings: UiSettings = {
    themeMode: 'auto',
    accentColor: '#1677ff',
    density: 'default',
    glass: true,
    backgroundType: 'gradient',
    backgroundImageUrl: '',
    backgroundGradient: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
    backgroundColor: '#0b1220',
    backgroundOpacity: 0.9,
    backgroundBlur: 8,
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
    if (settings.glass) {
      const bg = isDark ? 'rgba(0,0,0,0.25)' : 'rgba(255,255,255,0.6)'
      return {
        background: bg,
        backdropFilter: `blur(${settings.backgroundBlur}px)`,
        WebkitBackdropFilter: `blur(${settings.backgroundBlur}px)`,
        borderRadius: 8,
        boxShadow: isDark ? '0 4px 30px rgba(0,0,0,0.3)' : '0 4px 30px rgba(0,0,0,0.1)'
      }
    }
    return { background: isDark ? '#111a2c' : '#fff', borderRadius: 8 }
  }, [settings.glass, settings.backgroundBlur, isDark])

  const [settingsOpen, setSettingsOpen] = useState(false)

  const [apiStatus, setApiStatus] = useState<'ok' | 'down' | 'loading'>('loading')
  useEffect(() => {
    let active = true
    const ping = async () => {
      try { await health(); if (active) setApiStatus('ok') } catch { if (active) setApiStatus('down') }
    }
    ping()
    const t = setInterval(ping, 5000)
    return () => { active = false; clearInterval(t) }
  }, [])

  return (
    <ConfigProvider theme={{ algorithm: algorithms as any, token: tokenOverrides }}>
      <div style={bgStyle} />
      <Layout style={{ minHeight: '100vh', position: 'relative', zIndex: 1, background: 'transparent' }}>
        <Header style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{ color: '#fff', fontWeight: 700, marginRight: 24 }}>Runicorn Viewer</div>
          <Menu
            theme="dark"
            mode="horizontal"
            selectedKeys={selected}
            items={[
              { key: 'runs', icon: <UnorderedListOutlined />, label: <Link to="/runs">Runs</Link> },
            ]}
            style={{ flex: 1, minWidth: 0 }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {apiStatus === 'ok' && <Tag color="green">API OK</Tag>}
            {apiStatus === 'loading' && <Tag color="processing">API…</Tag>}
            {apiStatus === 'down' && <Tag>API DOWN</Tag>}
            <Button type="link" icon={<SettingOutlined style={{ color: '#fff' }} />} onClick={() => setSettingsOpen(true)} />
          </div>
        </Header>
        <Content style={{ padding: '24px' }}>
          <div style={{ ...wrapperStyle, padding: 24, minHeight: 360 }}>
            <Routes>
              <Route path="/" element={<RunsPage />} />
              <Route path="/runs" element={<RunsPage />} />
              <Route path="/runs/:id" element={<RunDetailPage />} />
            </Routes>
          </div>
        </Content>
        <Footer style={{ textAlign: 'center' }}> {new Date().getFullYear()} Runicorn Viewer</Footer>
      </Layout>
      <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} value={settings} onChange={setSettings} />
    </ConfigProvider>
  )
}
