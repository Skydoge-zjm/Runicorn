/**
 * Remote Viewer Page Animation Configuration
 */

export const remotePageConfig = {
  // Connection step progress
  stepProgress: {
    dotSize: 32,
    lineHeight: 2,
    lineColor: '#e8e8e8',
    
    completedColor: '#52c41a',
    activeGradient: ['#1677ff', '#4096ff'] as [string, string],
    inactiveColor: '#d9d9d9',
    
    labelFontSize: 14,
    labelFontWeight: 500,
    labelMarginTop: 12,
    
    pulseAnimation: {
      scale: [1, 1.2, 1],
      opacity: [1, 0.6, 1],
      transition: {
        duration: 1.5,
        ease: 'easeInOut' as const
      }
    }
  },
  
  // Server/Environment card
  serverCard: {
    borderRadius: 16,
    padding: 20,
    minHeight: 140,
    
    hoverEffect: {
      y: -4,
      scale: 1.01,
      boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
      transition: { duration: 0.3 }
    },
    
    selectedBorder: '2px solid #1677ff',
    selectedShadow: '0 0 0 4px rgba(22, 119, 255, 0.1)',
    
    iconSize: 48,
    iconColor: '#1677ff',
  },
  
  // Status light indicator
  statusLight: {
    size: 12,
    
    colors: {
      online: '#52c41a',
      offline: '#ff4d4f',
      connecting: '#faad14',
    },
    
    pulseAnimation: {
      boxShadow: [
        '0 0 0 0 rgba(82, 196, 26, 0.7)',
        '0 0 0 10px rgba(82, 196, 26, 0)',
      ],
      transition: {
        duration: 1.5,
        ease: 'easeOut' as const
      }
    }
  },
  
  // Connection card
  connectionCard: {
    borderRadius: 16,
    padding: 24,
    
    gradientBorder: {
      colors: ['#667eea', '#764ba2'] as [string, string],
      width: 2,
    },
    
    hoverEffect: {
      boxShadow: '0 8px 32px rgba(102, 126, 234, 0.2)',
      transition: { duration: 0.3 }
    }
  }
}

export default remotePageConfig

