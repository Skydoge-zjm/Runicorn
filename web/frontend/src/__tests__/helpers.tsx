import React from 'react'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { SettingsProvider } from '../contexts/SettingsContext'
import type { UiSettings } from '../components/settings/themePresets'

// Minimal mock for react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: vi.fn() },
  }),
  Trans: ({ children }: any) => children,
  initReactI18next: { type: '3rdParty', init: vi.fn() },
}))

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
}

export const defaultSettings: UiSettings = {
  themeMode: 'auto',
  accentColor: '#1677ff',
  density: 'default',
  glass: false,
  backgroundType: 'color',
  backgroundImageUrl: '',
  backgroundGradient: '',
  backgroundColor: '#F0F2F5',
  backgroundColorDark: '#0d0d12',
  backgroundOpacity: 0.9,
  backgroundBlur: 8,
  surfaceColor: '#ffffff',
  surfaceColorDark: '#1e1e2e',
  autoRefresh: false,
  refreshInterval: 5,
  animationsEnabled: true,
  enableSounds: false,
  defaultChartHeight: 300,
  showGridLines: true,
  enableChartAnimations: true,
  maxDataPoints: 500,
  compareTooltipShowId: false,
  showCpuTab: true,
  showMemoryDiskTab: true,
  showGpuMetricsTab: true,
  showGpuTelemetryTab: true,
}

/** Wrapper with QueryClient + MemoryRouter + SettingsProvider */
export function createWrapper(opts?: {
  initialEntries?: string[]
  settings?: UiSettings
}) {
  const qc = createTestQueryClient()
  const settings = opts?.settings ?? defaultSettings
  const routerFuture = {
    v7_startTransition: true,
    v7_relativeSplatPath: true,
  } as const

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <MemoryRouter
          initialEntries={opts?.initialEntries ?? ['/']}
          future={routerFuture}
        >
          <SettingsProvider value={{ settings, setSettings: vi.fn() }}>
            {children}
          </SettingsProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
}

export function renderWithProviders(
  ui: React.ReactElement,
  opts?: {
    initialEntries?: string[]
    settings?: UiSettings
  },
) {
  return render(ui, { wrapper: createWrapper(opts) })
}
