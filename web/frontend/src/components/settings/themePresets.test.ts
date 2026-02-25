import { describe, it, expect } from 'vitest'
import {
  themePresets,
  detectActivePreset,
  type UiSettings,
  type ThemePreset,
} from './themePresets'

// ── themePresets data integrity ──

describe('themePresets data integrity', () => {
  it('has unique keys', () => {
    const keys = themePresets.map((p) => p.key)
    expect(new Set(keys).size).toBe(keys.length)
  })

  it.each(themePresets)('preset "$key" has labelKey', (preset: ThemePreset) => {
    expect(preset.labelKey).toBeTruthy()
    expect(typeof preset.labelKey).toBe('string')
  })

  it.each(themePresets)('preset "$key" has swatch of length 2', (preset: ThemePreset) => {
    expect(preset.swatch).toHaveLength(2)
  })

  it.each(themePresets)(
    'preset "$key" has valid themeMode in settings',
    (preset: ThemePreset) => {
      if (preset.settings.themeMode !== undefined) {
        expect(['light', 'dark', 'auto']).toContain(preset.settings.themeMode)
      }
    },
  )
})

// ── detectActivePreset ──

describe('detectActivePreset', () => {
  function buildSettings(preset: ThemePreset): UiSettings {
    // Build a full UiSettings with defaults, overridden by preset.settings
    return {
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
      refreshInterval: 5000,
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
      ...preset.settings,
    }
  }

  it('detects "default" preset', () => {
    const preset = themePresets.find((p) => p.key === 'default')!
    const settings = buildSettings(preset)
    expect(detectActivePreset(settings)).toBe('default')
  })

  it('detects "minimal" preset', () => {
    const preset = themePresets.find((p) => p.key === 'minimal')!
    const settings = buildSettings(preset)
    expect(detectActivePreset(settings)).toBe('minimal')
  })

  it('returns undefined when settings do not match any preset', () => {
    const preset = themePresets.find((p) => p.key === 'default')!
    const settings = buildSettings(preset)
    settings.accentColor = '#ff0000' // mutate one field
    expect(detectActivePreset(settings)).toBeUndefined()
  })

  it('returns undefined for fully custom settings', () => {
    const custom: UiSettings = {
      themeMode: 'dark',
      accentColor: '#abc123',
      density: 'loose',
      glass: true,
      backgroundType: 'image',
      backgroundImageUrl: 'https://example.com/bg.jpg',
      backgroundGradient: '',
      backgroundColor: '#000',
      backgroundColorDark: '#000',
      backgroundOpacity: 0.5,
      backgroundBlur: 20,
      surfaceColor: '#111',
      surfaceColorDark: '#222',
      autoRefresh: true,
      refreshInterval: 1000,
      animationsEnabled: false,
      enableSounds: true,
      defaultChartHeight: 200,
      showGridLines: false,
      enableChartAnimations: false,
      maxDataPoints: 100,
      compareTooltipShowId: true,
      showCpuTab: false,
      showMemoryDiskTab: false,
      showGpuMetricsTab: false,
      showGpuTelemetryTab: false,
    }
    expect(detectActivePreset(custom)).toBeUndefined()
  })
})
