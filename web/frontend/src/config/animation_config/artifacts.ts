/**
 * Artifacts Page Animation Configuration
 */

export const artifactsPageConfig = {
  // Artifact card
  artifactCard: {
    borderRadius: 16,
    padding: 20,
    minHeight: 180,
    
    hoverEffect: {
      y: -6,
      scale: 1.02,
      rotateY: 2,  // Subtle 3D effect
      transition: { duration: 0.3 }
    },
    
    // Version badge
    versionBadge: {
      fontSize: 13,
      fontWeight: 600,
      padding: '4px 12px',
      borderRadius: 12,
      background: ['#667eea', '#764ba2'] as [string, string],
    },
    
    // File count badge
    fileBadge: {
      background: '#52c41a',
      color: '#fff',
    },
  },
  
  // Storage ring chart
  storageRing: {
    size: 200,
    strokeWidth: 20,
    
    // Colors for different segments
    colors: {
      used: ['#1677ff', '#4096ff'] as [string, string],
      saved: ['#52c41a', '#73d13d'] as [string, string],
      available: ['#f0f0f0', '#e6e6e6'] as [string, string],
    },
    
    animation: {
      duration: 1.5,
      ease: [0.25, 0.1, 0.25, 1] as [number, number, number, number]
    },
    
    labelFontSize: 32,
    labelFontWeight: 700,
    sublabelFontSize: 14,
  },
  
  // Version timeline
  timeline: {
    dotSize: 12,
    lineWidth: 2,
    lineColor: '#e8e8e8',
    
    activeDotGradient: ['#1677ff', '#4096ff'] as [string, string],
    inactiveDotColor: '#d9d9d9',
    
    cardBorderRadius: 12,
    cardPadding: 16,
    cardShadow: '0 2px 8px rgba(0,0,0,0.06)',
  }
}

export default artifactsPageConfig

