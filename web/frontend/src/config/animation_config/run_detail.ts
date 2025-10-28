/**
 * Run Detail Page Animation Configuration
 */

export const runDetailPageConfig = {
  // Metric chart card
  metricCard: {
    borderRadius: 16,
    boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
    
    hoverEffect: {
      y: -4,
      boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
      transition: { duration: 0.3 }
    },
    
    headerGradient: ['#667eea', '#764ba2'] as [string, string],
    headerPadding: 16,
    headerIconColor: '#1677ff',
    headerFontSize: 16,
    headerFontWeight: 600,
  },
  
  // GPU Circular Progress
  gpuProgress: {
    size: 120,
    strokeWidth: 8,
    
    colors: {
      low: ['#52c41a', '#73d13d'] as [string, string],     // <50%: green
      medium: ['#faad14', '#ffc53d'] as [string, string],  // 50-80%: yellow
      high: ['#ff4d4f', '#ff7875'] as [string, string],    // >80%: red
    },
    
    animation: {
      duration: 1.5,
      ease: [0.25, 0.1, 0.25, 1] as [number, number, number, number]
    },
    
    labelFontSize: 28,
    labelFontWeight: 700,
    sublabelFontSize: 12,
    sublabelColor: '#8c8c8c',
  },
  
  // Tabs animation
  tabs: {
    contentFadeIn: {
      initial: { opacity: 0, y: 10 },
      animate: { opacity: 1, y: 0 },
      transition: { duration: 0.3 }
    }
  },
  
  // Description items
  descriptionItem: {
    labelColor: '#8c8c8c',
    valueColor: '#262626',
    valueFontWeight: 500,
  }
}

export default runDetailPageConfig

