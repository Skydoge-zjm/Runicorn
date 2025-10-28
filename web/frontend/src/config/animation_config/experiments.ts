/**
 * Experiments Page Animation Configuration
 * 
 * Page-specific animation parameters for ExperimentPage
 */

import { animationConfig } from './common'

export const experimentsPageConfig = {
  // Page title animation
  title: {
    initial: { x: -30, opacity: 0 },
    animate: { x: 0, opacity: 1 },
    transition: { duration: 0.6 },
    
    fontSize: 36,
    fontWeight: 700,
    marginBottom: 8,
    lineHeight: 1.2,
  },
  
  // Subtitle
  subtitle: {
    fontSize: 15,
    color: '#8c8c8c',
    fontWeight: 400,
  },
  
  // Fancy stat cards configuration
  statCards: {
    total: {
      gradientColors: ['#434343', '#000000'] as [string, string],  // Dark/black theme for white text
      delay: 0,
      pulse: false,
    },
    running: {
      gradientColors: ['#1890ff', '#096dd9'] as [string, string],  // Blue theme matching running tag
      delay: 0.1,
      pulse: true,  // Will be conditional based on value > 0
    },
    finished: {
      gradientColors: ['#52c41a', '#389e0d'] as [string, string],  // Green theme matching success tag
      delay: 0.2,
      pulse: false,
    },
    failed: {
      gradientColors: ['#ff4d4f', '#cf1322'] as [string, string],  // Red theme matching error tag
      delay: 0.3,
      pulse: false,
    },
    
    // Common card settings
    minHeight: 140,
    borderRadius: 16,
    iconSize: 140,
    iconOpacity: 0.12,
    iconOffset: { right: -30, top: -30 },
    
    titleFontSize: 14,
    titleFontWeight: 500,
    titleLetterSpacing: '0.5px',
    titleOpacity: 0.95,
    
    valueFontSize: 40,
    valueFontWeight: 700,
    valueTextShadow: '0 2px 8px rgba(0,0,0,0.15)',
  },
  
  // Filter card animation
  filterCard: {
    animation: {
      initial: { opacity: 0, y: 20 },
      animate: { opacity: 1, y: 0 },
      transition: { delay: 0.5 }
    },
    
    borderRadius: 16,
    background: 'rgba(255,255,255,0.7)',
    backdropFilter: 'blur(12px)',
    border: '1px solid rgba(255,255,255,0.3)',
    boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
    padding: 20,
  },
  
  // Table container animation
  tableContainer: {
    animation: {
      initial: { opacity: 0, y: 20 },
      animate: { opacity: 1, y: 0 },
      transition: { delay: 0.6 }
    },
    
    borderRadius: 16,
    boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
  },
  
  // Confetti configuration
  confetti: {
    particleCount: 20,
    colors: ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#13c2c2'],
    duration: 1.5,
    displayTime: 2000,  // ms
    
    // Explosion parameters
    baseDistance: 200,
    randomDistance: 200,
    yOffset: -200,
    
    // Particle size
    minSize: 8,
    maxSize: 16,
  },
  
  // Empty state configuration
  emptyState: {
    illustrationSize: 200,
    padding: '80px 40px',
    maxWidth: 500,
    
    titleFontSize: 24,
    titleFontWeight: 600,
    titleMarginTop: 32,
    titleMarginBottom: 12,
    
    descriptionFontSize: 15,
    descriptionColor: '#8c8c8c',
    descriptionLineHeight: 1.6,
    descriptionMaxWidth: 400,
    
    buttonHeight: 48,
    buttonPadding: '0 32px',
    buttonFontSize: 15,
    buttonBorderRadius: 8,
    buttonShadow: '0 4px 16px rgba(22, 119, 255, 0.3)',
  }
}

export default experimentsPageConfig

