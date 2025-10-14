/**
 * Runicorn Design System - Design Tokens
 * 
 * Unified design variables for consistent UI/UX
 */

export const designTokens = {
  // Spacing System (8px base)
  spacing: {
    xs: 8,
    sm: 12,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },

  // Border Radius
  borderRadius: {
    sm: 6,
    md: 8,
    lg: 12,
    xl: 16,
    round: '50%',
  },

  // Color Palette
  colors: {
    primary: '#1677ff',
    success: '#52c41a',
    warning: '#faad14',
    error: '#ff4d4f',
    info: '#13c2c2',
    
    // Status Colors
    status: {
      running: '#1677ff',    // Blue
      finished: '#52c41a',   // Green
      failed: '#ff4d4f',     // Red
      interrupted: '#faad14', // Orange
    },
    
    // Neutral Colors (for dark/light modes)
    neutral: {
      light: {
        bg: '#ffffff',
        bgSecondary: '#fafafa',
        border: 'rgba(0, 0, 0, 0.06)',
        text: 'rgba(0, 0, 0, 0.88)',
        textSecondary: 'rgba(0, 0, 0, 0.65)',
        textTertiary: 'rgba(0, 0, 0, 0.45)',
      },
      dark: {
        bg: '#141414',
        bgSecondary: '#1f1f1f',
        border: 'rgba(255, 255, 255, 0.12)',
        text: 'rgba(255, 255, 255, 0.88)',
        textSecondary: 'rgba(255, 255, 255, 0.65)',
        textTertiary: 'rgba(255, 255, 255, 0.45)',
      },
    },
  },

  // Typography
  typography: {
    fontSize: {
      xs: 12,
      sm: 14,
      md: 16,
      lg: 18,
      xl: 20,
      xxl: 24,
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.75,
    },
  },

  // Shadows
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
    glass: {
      light: '0 8px 32px rgba(0, 0, 0, 0.12)',
      dark: '0 8px 32px rgba(0, 0, 0, 0.4)',
    },
  },

  // Transitions
  transitions: {
    fast: '150ms ease-in-out',
    normal: '250ms ease-in-out',
    slow: '350ms ease-in-out',
  },

  // Z-index Layers
  zIndex: {
    base: 0,
    dropdown: 1000,
    sticky: 1020,
    fixed: 1030,
    modalBackdrop: 1040,
    modal: 1050,
    popover: 1060,
    tooltip: 1070,
  },

  // Glass Effect
  glass: {
    light: {
      background: 'rgba(255, 255, 255, 0.75)',
      backdropFilter: 'blur(12px) saturate(180%)',
      border: '1px solid rgba(255, 255, 255, 0.3)',
      shadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
    },
    dark: {
      background: 'rgba(30, 30, 30, 0.75)',
      backdropFilter: 'blur(12px) saturate(180%)',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      shadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
    },
  },

  // Breakpoints (for responsive design)
  breakpoints: {
    xs: 480,
    sm: 576,
    md: 768,
    lg: 992,
    xl: 1200,
    xxl: 1600,
  },
}

// Helper function to get responsive value
export const getResponsiveValue = <T>(
  values: Partial<Record<keyof typeof designTokens.breakpoints, T>>,
  currentWidth: number
): T | undefined => {
  const breakpoints = Object.entries(designTokens.breakpoints).sort(([, a], [, b]) => b - a)
  
  for (const [key, width] of breakpoints) {
    if (currentWidth >= width && values[key as keyof typeof values]) {
      return values[key as keyof typeof values]
    }
  }
  
  return Object.values(values)[0]
}

export default designTokens
