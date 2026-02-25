/**
 * Theme Presets & Appearance Types
 *
 * Defines UiSettings, gradient presets, theme presets,
 * and the active-preset detection helper.
 */

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
  /** Background color for dark mode (used when backgroundType === 'color') */
  backgroundColorDark: string
  /** Surface / container color (light mode) – controls header, panels, cards, tables */
  surfaceColor: string
  /** Surface / container color (dark mode) */
  surfaceColorDark: string
  
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

  /** Compare charts: show run ID instead of alias in tooltip */
  compareTooltipShowId: boolean
  
  // Performance Monitor Tab Settings
  showCpuTab: boolean
  showMemoryDiskTab: boolean
  showGpuMetricsTab: boolean
  showGpuTelemetryTab: boolean
}

export const gradientPresets: { label: string; value: string }[] = [
  { label: 'Aurora', value: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)' },
  { label: 'Sunset', value: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)' },
  { label: 'Ocean', value: 'linear-gradient(135deg, #5ee7df 0%, #b490ca 100%)' },
  { label: 'Forest', value: 'linear-gradient(135deg, #a8e063 0%, #56ab2f 100%)' },
]

/** Theme presets — only override appearance-related fields. */
export interface ThemePreset {
  key: string
  labelKey: string
  /** 2-color gradient used for the swatch dot in the dropdown */
  swatch: [string, string]
  settings: Partial<UiSettings>
}

export const themePresets: ThemePreset[] = [
  // ── Defaults ──
  {
    key: 'default',
    labelKey: 'settings.preset.default',
    swatch: ['#1677ff', '#e6f4ff'],
    settings: {
      themeMode: 'auto', accentColor: '#1677ff',
      glass: false, backgroundType: 'color',
      backgroundColor: '#F0F2F5', backgroundColorDark: '#0d0d12',
      surfaceColor: '#ffffff', surfaceColorDark: '#1e1e2e',
      backgroundOpacity: 0.9, backgroundBlur: 8,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
  {
    key: 'default_light',
    labelKey: 'settings.preset.default_light',
    swatch: ['#1677ff', '#ffffff'],
    settings: {
      themeMode: 'light', accentColor: '#1677ff',
      glass: false, backgroundType: 'color',
      backgroundColor: '#F0F2F5', backgroundColorDark: '#0d0d12',
      surfaceColor: '#ffffff', surfaceColorDark: '#1e1e2e',
      backgroundOpacity: 0.9, backgroundBlur: 8,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
  {
    key: 'default_dark',
    labelKey: 'settings.preset.default_dark',
    swatch: ['#1677ff', '#1e1e2e'],
    settings: {
      themeMode: 'dark', accentColor: '#1677ff',
      glass: false, backgroundType: 'color',
      backgroundColor: '#F0F2F5', backgroundColorDark: '#0d0d12',
      surfaceColor: '#ffffff', surfaceColorDark: '#1e1e2e',
      backgroundOpacity: 0.9, backgroundBlur: 8,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },

  // ── Neutral / Black & White ──
  {
    key: 'minimal',
    labelKey: 'settings.preset.minimal',
    swatch: ['#333333', '#ffffff'],
    settings: {
      themeMode: 'light', accentColor: '#333333',
      glass: false, backgroundType: 'color',
      backgroundColor: '#f5f5f5', backgroundColorDark: '#111111',
      surfaceColor: '#ffffff', surfaceColorDark: '#1e1e1e',
      backgroundOpacity: 1, backgroundBlur: 0,
      animationsEnabled: false, enableChartAnimations: false,
    },
  },
  {
    key: 'slate',
    labelKey: 'settings.preset.slate',
    swatch: ['#64748b', '#f1f5f9'],
    settings: {
      themeMode: 'auto', accentColor: '#64748b',
      glass: false, backgroundType: 'color',
      backgroundColor: '#f1f5f9', backgroundColorDark: '#0f172a',
      surfaceColor: '#ffffff', surfaceColorDark: '#1e293b',
      backgroundOpacity: 1, backgroundBlur: 0,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
  {
    key: 'ink_wash',
    labelKey: 'settings.preset.ink_wash',
    swatch: ['#8a9aa5', '#1a1a1a'],
    settings: {
      themeMode: 'dark', accentColor: '#5c6d7a',
      glass: false, backgroundType: 'color',
      backgroundColor: '#f5f5f5', backgroundColorDark: '#121212',
      surfaceColor: '#ffffff', surfaceColorDark: '#1e1e1e',
      backgroundOpacity: 1, backgroundBlur: 0,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
  {
    key: 'amoled_black',
    labelKey: 'settings.preset.amoled_black',
    swatch: ['#ffffff', '#000000'],
    settings: {
      themeMode: 'dark', accentColor: '#3b82f6',
      glass: false, backgroundType: 'color',
      backgroundColor: '#f5f5f5', backgroundColorDark: '#000000',
      surfaceColor: '#ffffff', surfaceColorDark: '#0a0a0a',
      backgroundOpacity: 1, backgroundBlur: 0,
      animationsEnabled: false, enableChartAnimations: false,
    },
  },

  // ── Blue / Cyan ──
  {
    key: 'arctic_blue',
    labelKey: 'settings.preset.arctic_blue',
    swatch: ['#0ea5e9', '#e0f2fe'],
    settings: {
      themeMode: 'light', accentColor: '#0284c7',
      glass: true, backgroundType: 'gradient',
      backgroundGradient: 'linear-gradient(135deg, #e0f2fe 0%, #bae6fd 40%, #7dd3fc 100%)',
      surfaceColor: 'rgba(240,249,255,0.48)', surfaceColorDark: 'rgba(8,28,42,0.45)',
      backgroundOpacity: 0.85, backgroundBlur: 10,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
  {
    key: 'cyber_neon',
    labelKey: 'settings.preset.cyber_neon',
    swatch: ['#22d3ee', '#0a0a14'],
    settings: {
      themeMode: 'dark', accentColor: '#0891b2',
      glass: false, backgroundType: 'color',
      backgroundColor: '#F0F2F5', backgroundColorDark: '#050510',
      surfaceColor: '#ffffff', surfaceColorDark: '#0f1a2e',
      backgroundOpacity: 1, backgroundBlur: 0,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
  {
    key: 'ocean_breeze',
    labelKey: 'settings.preset.ocean_breeze',
    swatch: ['#5ee7df', '#b490ca'],
    settings: {
      themeMode: 'light', accentColor: '#0d9488',
      glass: true, backgroundType: 'gradient',
      backgroundGradient: 'linear-gradient(135deg, #5ee7df 0%, #b490ca 100%)',
      surfaceColor: 'rgba(245,255,252,0.48)', surfaceColorDark: 'rgba(16,24,30,0.45)',
      backgroundOpacity: 0.85, backgroundBlur: 10,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
  {
    key: 'aurora_glass',
    labelKey: 'settings.preset.aurora_glass',
    swatch: ['#30cfd0', '#330867'],
    settings: {
      themeMode: 'auto', accentColor: '#0e9aa0',
      glass: true, backgroundType: 'gradient',
      backgroundGradient: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
      surfaceColor: 'rgba(255,255,255,0.42)', surfaceColorDark: 'rgba(16,16,42,0.48)',
      backgroundOpacity: 0.85, backgroundBlur: 12,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },

  // ── Indigo / Purple ──
  {
    key: 'frosted_glass',
    labelKey: 'settings.preset.frosted_glass',
    swatch: ['#6366f1', '#e0e7ff'],
    settings: {
      themeMode: 'auto', accentColor: '#6366f1',
      glass: true, backgroundType: 'gradient',
      backgroundGradient: 'linear-gradient(135deg, #c7d2fe 0%, #e0e7ff 50%, #ddd6fe 100%)',
      surfaceColor: 'rgba(255,255,255,0.3)', surfaceColorDark: 'rgba(22,22,48,0.35)',
      backgroundOpacity: 0.75, backgroundBlur: 18,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
  {
    key: 'deep_space',
    labelKey: 'settings.preset.deep_space',
    swatch: ['#818cf8', '#020617'],
    settings: {
      themeMode: 'dark', accentColor: '#6366f1',
      glass: true, backgroundType: 'gradient',
      backgroundGradient: 'linear-gradient(135deg, #020617 0%, #0f172a 40%, #1e1b4b 100%)',
      surfaceColor: 'rgba(255,255,255,0.45)', surfaceColorDark: 'rgba(10,16,40,0.42)',
      backgroundOpacity: 0.9, backgroundBlur: 8,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
  {
    key: 'lavender_haze',
    labelKey: 'settings.preset.lavender_haze',
    swatch: ['#8b5cf6', '#ede9fe'],
    settings: {
      themeMode: 'light', accentColor: '#8b5cf6',
      glass: true, backgroundType: 'gradient',
      backgroundGradient: 'linear-gradient(135deg, #ede9fe 0%, #ddd6fe 40%, #c4b5fd 100%)',
      surfaceColor: 'rgba(250,245,255,0.48)', surfaceColorDark: 'rgba(24,16,42,0.45)',
      backgroundOpacity: 0.85, backgroundBlur: 10,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
  {
    key: 'midnight_purple',
    labelKey: 'settings.preset.midnight_purple',
    swatch: ['#a855f7', '#1a0533'],
    settings: {
      themeMode: 'dark', accentColor: '#a855f7',
      glass: true, backgroundType: 'gradient',
      backgroundGradient: 'linear-gradient(135deg, #1a0533 0%, #0f0326 40%, #2d1b69 100%)',
      surfaceColor: 'rgba(255,255,255,0.45)', surfaceColorDark: 'rgba(28,16,52,0.42)',
      backgroundOpacity: 0.8, backgroundBlur: 14,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },

  // ── Pink / Rose ──
  {
    key: 'rose_dawn',
    labelKey: 'settings.preset.rose_dawn',
    swatch: ['#ec4899', '#fce7f3'],
    settings: {
      themeMode: 'light', accentColor: '#ec4899',
      glass: true, backgroundType: 'gradient',
      backgroundGradient: 'linear-gradient(135deg, #fce7f3 0%, #fda4af 50%, #fecdd3 100%)',
      surfaceColor: 'rgba(255,248,252,0.48)', surfaceColorDark: 'rgba(38,20,28,0.45)',
      backgroundOpacity: 0.85, backgroundBlur: 10,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
  {
    key: 'cherry_blossom',
    labelKey: 'settings.preset.cherry_blossom',
    swatch: ['#f472b6', '#fff1f2'],
    settings: {
      themeMode: 'light', accentColor: '#db2777',
      glass: true, backgroundType: 'gradient',
      backgroundGradient: 'linear-gradient(135deg, #fff1f2 0%, #ffe4e6 40%, #fecdd3 100%)',
      surfaceColor: 'rgba(255,250,253,0.48)', surfaceColorDark: 'rgba(35,18,24,0.45)',
      backgroundOpacity: 0.85, backgroundBlur: 10,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },

  // ── Orange / Amber / Warm ──
  {
    key: 'warm_sunset',
    labelKey: 'settings.preset.warm_sunset',
    swatch: ['#f6d365', '#fda085'],
    settings: {
      themeMode: 'light', accentColor: '#d97706',
      glass: true, backgroundType: 'gradient',
      backgroundGradient: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)',
      surfaceColor: 'rgba(255,252,245,0.48)', surfaceColorDark: 'rgba(30,22,16,0.45)',
      backgroundOpacity: 0.85, backgroundBlur: 10,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
  {
    key: 'ember_glow',
    labelKey: 'settings.preset.ember_glow',
    swatch: ['#f59e0b', '#1c1108'],
    settings: {
      themeMode: 'dark', accentColor: '#b45309',
      glass: true, backgroundType: 'gradient',
      backgroundGradient: 'linear-gradient(135deg, #1c1108 0%, #271a0a 40%, #422006 100%)',
      surfaceColor: 'rgba(255,252,245,0.45)', surfaceColorDark: 'rgba(30,20,8,0.42)',
      backgroundOpacity: 0.85, backgroundBlur: 12,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },

  // ── Green ──
  {
    key: 'forest_mist',
    labelKey: 'settings.preset.forest_mist',
    swatch: ['#22c55e', '#ecfdf5'],
    settings: {
      themeMode: 'light', accentColor: '#15803d',
      glass: true, backgroundType: 'gradient',
      backgroundGradient: 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 40%, #a7f3d0 100%)',
      surfaceColor: 'rgba(240,253,244,0.48)', surfaceColorDark: 'rgba(10,30,18,0.45)',
      backgroundOpacity: 0.85, backgroundBlur: 10,
      animationsEnabled: true, enableChartAnimations: true,
    },
  },
]

/** Detect which preset matches the current appearance settings. */
export function detectActivePreset(current: UiSettings): string | undefined {
  for (const preset of themePresets) {
    const match = Object.entries(preset.settings).every(
      ([key, val]) => (current as any)[key] === val
    )
    if (match) return preset.key
  }
  return undefined
}
