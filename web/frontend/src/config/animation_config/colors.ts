/**
 * Color Configuration for Fancy UI
 * 
 * All colors, gradients, and visual styling
 */

export const colorConfig = {
  // Gradient color pairs
  gradients: {
    // Statistics cards
    stats: {
      total: ['#667eea', '#764ba2'] as [string, string],
      running: ['#f093fb', '#f5576c'] as [string, string],
      finished: ['#4facfe', '#00f2fe'] as [string, string],
      failed: ['#fa709a', '#fee140'] as [string, string],
    },
    
    // General purpose
    primary: ['#667eea', '#764ba2'] as [string, string],
    secondary: ['#f093fb', '#f5576c'] as [string, string],
    success: ['#56ab2f', '#a8e063'] as [string, string],
    warning: ['#f12711', '#f5af19'] as [string, string],
    error: ['#eb3349', '#f45c43'] as [string, string],
    info: ['#4facfe', '#00f2fe'] as [string, string],
    
    // Special gradients
    royal: ['#8e2de2', '#4a00e0'] as [string, string],
    ocean: ['#2e3192', '#1bffff'] as [string, string],
    sunset: ['#fa709a', '#fee140'] as [string, string],
    rainbow: ['#ff6e7f', '#bfe9ff'] as [string, string],
  },
  
  // Status colors
  status: {
    running: {
      primary: '#1677ff',
      gradient: ['#1677ff', '#4096ff'] as [string, string],
    },
    finished: {
      primary: '#52c41a',
      gradient: ['#52c41a', '#73d13d'] as [string, string],
    },
    failed: {
      primary: '#ff4d4f',
      gradient: ['#ff4d4f', '#ff7875'] as [string, string],
    },
    interrupted: {
      primary: '#faad14',
      gradient: ['#faad14', '#ffc53d'] as [string, string],
    }
  },
  
  // Semantic colors
  semantic: {
    primary: '#1677ff',
    success: '#52c41a',
    warning: '#faad14',
    error: '#ff4d4f',
    info: '#13c2c2',
  },
  
  // Text colors
  text: {
    primary: '#262626',
    secondary: '#8c8c8c',
    tertiary: '#bfbfbf',
    inverse: '#ffffff',
  },
  
  // Background colors
  backgrounds: {
    white: '#ffffff',
    light: '#fafafa',
    lightGray: '#f5f5f5',
    glass: 'rgba(255,255,255,0.7)',
    glassBlur: 'blur(12px)',
  },
  
  // Shadow colors
  shadows: {
    sm: '0 2px 8px rgba(0,0,0,0.06)',
    md: '0 4px 16px rgba(0,0,0,0.08)',
    lg: '0 8px 24px rgba(0,0,0,0.12)',
    xl: '0 12px 32px rgba(0,0,0,0.16)',
    
    // Colored shadows
    primary: '0 4px 16px rgba(22, 119, 255, 0.3)',
    success: '0 4px 16px rgba(82, 196, 26, 0.25)',
    error: '0 4px 16px rgba(255, 77, 79, 0.25)',
  }
}

// Helper function to create gradient CSS string
export const createGradient = (
  colors: [string, string], 
  angle: number = 135
): string => {
  return `linear-gradient(${angle}deg, ${colors[0]}, ${colors[1]})`
}

// Helper function to create radial gradient
export const createRadialGradient = (
  colors: [string, string]
): string => {
  return `radial-gradient(circle, ${colors[0]}, ${colors[1]})`
}

export default colorConfig

