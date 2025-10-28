/**
 * Gradient Color System
 * 
 * Unified gradient colors for consistent fancy UI
 */

export const gradients = {
  // Statistics card gradients
  stats: {
    total: ['#667eea', '#764ba2'],      // Purple-blue: tech, professional
    running: ['#f093fb', '#f5576c'],    // Pink-red: vibrant, active
    finished: ['#4facfe', '#00f2fe'],   // Blue: cool, success
    failed: ['#fa709a', '#fee140'],     // Orange-yellow: warm, warning
  },
  
  // General purpose gradients
  backgrounds: {
    primary: ['#667eea', '#764ba2'],
    secondary: ['#f093fb', '#f5576c'],
    success: ['#56ab2f', '#a8e063'],
    warning: ['#f12711', '#f5af19'],
    error: ['#eb3349', '#f45c43'],
    info: ['#4facfe', '#00f2fe'],
  },
  
  // Button gradients
  buttons: {
    primary: ['#667eea', '#764ba2'],
    success: ['#56ab2f', '#a8e063'],
    danger: ['#ff416c', '#ff4b2b'],
  },
  
  // Background gradients
  pages: {
    default: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    vibrant: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    ocean: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    sunset: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  }
}

/**
 * Helper function to create CSS gradient string
 */
export const createGradient = (colors: [string, string], angle: number = 135): string => {
  return `linear-gradient(${angle}deg, ${colors[0]}, ${colors[1]})`
}

/**
 * Helper function to create radial gradient
 */
export const createRadialGradient = (colors: [string, string]): string => {
  return `radial-gradient(circle, ${colors[0]}, ${colors[1]})`
}

export default gradients

