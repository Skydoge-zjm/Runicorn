/**
 * Component-specific Animation Configuration
 * 
 * Reusable component animation parameters
 */

export const componentAnimationConfig = {
  // FancyStatCard
  fancyStatCard: {
    // Card entrance animation
    entrance: {
      initial: { opacity: 0, y: 30, scale: 0.9 },
      animate: { opacity: 1, y: 0, scale: 1 },
      transition: {
        duration: 0.6,
        ease: [0.25, 0.1, 0.25, 1] as [number, number, number, number]
      }
    },
    
    // Hover effect
    hover: {
      y: -6,
      scale: 1.03,
      transition: { duration: 0.2 }
    },
    
    // Tap effect
    tap: {
      scale: 0.98
    },
    
    // Pulse effect (for active states)
    pulse: {
      animate: {
        scale: [1, 1.2, 1],
        opacity: [0.3, 0.6, 0.3]
      },
      transition: {
        duration: 2,
        ease: 'easeInOut' as const
      }
    },
    
    // Shimmer effect
    shimmer: {
      animate: {
        left: ['100%', '200%']
      },
      transition: {
        duration: 2.5,
        repeatDelay: 5,
        ease: 'linear' as const
      }
    },
    
    // Styling
    style: {
      borderRadius: 16,
      minHeight: 140,
      boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
      
      // Background icon
      iconSize: 140,
      iconOpacity: 0.12,
      iconPosition: { right: -30, top: -30 },
      
      // Title
      titleFontSize: 14,
      titleFontWeight: 500,
      titleLetterSpacing: '0.5px',
      titleColor: 'rgba(255,255,255,0.95)',
      titleMarginBottom: 12,
      
      // Value
      valueFontSize: 40,
      valueFontWeight: 700,
      valueColor: '#fff',
      valueTextShadow: '0 2px 8px rgba(0,0,0,0.15)',
    },
    
    // Number animation configuration (DEPRECATED - now using tween animation)
    // The component now uses easeOut tween for smooth count-up without bounce
    // This config is kept for backward compatibility but no longer used
    spring: {
      damping: 50,      // [UNUSED] Previously: High damping for ultra-smooth
      stiffness: 300    // [UNUSED] Previously: High stiffness for fast animation
    }
  },
  
  // AnimatedStatusBadge
  statusBadge: {
    // Entrance animation
    entrance: {
      initial: { scale: 0, opacity: 0 },
      animate: { scale: 1, opacity: 1 },
      transition: {
        type: 'spring' as const,
        stiffness: 260,
        damping: 20
      }
    },
    
    // Pulse animation for running status
    pulse: {
      boxShadow: [
        '0 0 0 0 rgba(22, 119, 255, 0.4)',
        '0 0 0 8px rgba(22, 119, 255, 0)',
      ],
      transition: {
        duration: 1.5,
        ease: 'easeOut' as const
      }
    },
    
    // Styling
    style: {
      fontSize: 13,
      padding: '6px 16px',
      borderRadius: 16,
      fontWeight: 500,
    },
    
    // Status-specific configurations
    statuses: {
      running: {
        gradientColors: ['#1677ff', '#4096ff'] as [string, string],
        pulse: true,
      },
      finished: {
        gradientColors: ['#52c41a', '#73d13d'] as [string, string],
        pulse: false,
      },
      failed: {
        gradientColors: ['#ff4d4f', '#ff7875'] as [string, string],
        pulse: false,
      },
      interrupted: {
        gradientColors: ['#faad14', '#ffc53d'] as [string, string],
        pulse: false,
      }
    }
  },
  
  // FancyEmpty
  emptyState: {
    // Container animation
    animation: {
      initial: { opacity: 0, scale: 0.9 },
      animate: { opacity: 1, scale: 1 },
      transition: { duration: 0.5 }
    },
    
    // Illustration float animation
    illustrationFloat: {
      animate: {
        y: [0, -8, 0]
      },
      transition: {
        duration: 3,
        ease: 'easeInOut' as const
      }
    },
    
    // SVG sizes and colors
    svg: {
      width: 200,
      height: 200,
      
      circleStroke: '#91caff',
      circleStrokeWidth: 2,
      circleDashArray: '10 5',
      circleRadius: 80,
      circleRotationDuration: 30,
      
      folderFill: '#91caff',
      folderFillOpacity: 0.8,
      folderTabFill: '#69b1ff',
      
      magnifierStroke: '#1677ff',
      magnifierStrokeWidth: 2.5,
      magnifierRadius: 12,
      magnifierMoveDuration: 2,
      magnifierMoveDistance: 3,
      
      dotCount: 6,
      dotRadius: 2,
      dotFill: '#1677ff',
      dotOpacity: 0.4,
      dotFloatDistance: -8,
      dotFloatDuration: 1.5,
      dotStaggerDelay: 0.15,
    },
    
    // Container styling
    style: {
      padding: '80px 40px',
      maxWidth: 500,
      
      titleFontSize: 24,
      titleFontWeight: 600,
      titleColor: '#262626',
      titleMarginTop: 32,
      titleMarginBottom: 12,
      titleLineHeight: 1.3,
      
      descriptionFontSize: 15,
      descriptionColor: '#8c8c8c',
      descriptionLineHeight: 1.6,
      descriptionMarginBottom: 32,
      descriptionMaxWidth: 400,
      
      buttonHeight: 48,
      buttonPadding: '0 32px',
      buttonFontSize: 15,
      buttonFontWeight: 500,
      buttonBorderRadius: 8,
      buttonShadow: '0 4px 16px rgba(22, 119, 255, 0.3)',
      buttonGradient: ['#667eea', '#764ba2'] as [string, string],
    },
    
    // Button animations
    buttonHover: {
      scale: 1.05
    },
    buttonTap: {
      scale: 0.95
    }
  },
  
  // Shimmer Skeleton
  shimmerSkeleton: {
    // Animation
    animate: {
      left: ['100%', '200%']
    },
    transition: {
      duration: 1.2,
      ease: 'linear' as const
    },
    
    // Styling
    backgroundColor: '#f0f0f0',
    shimmerGradient: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.9), transparent)',
    defaultBorderRadius: 4,
    defaultHeight: 20,
  },
  
  // Success Confetti
  confetti: {
    particleCount: 20,
    colors: ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#13c2c2'],
    duration: 1.5,
    displayTime: 2000,
    
    // Explosion parameters
    baseDistance: 200,
    randomDistance: 200,
    yOffset: -200,
    
    // Particle size range
    minSize: 8,
    sizeRange: 8,  // minSize + random(0, sizeRange)
    
    // Center burst
    centerBurst: {
      size: 100,
      scale: 3,
      duration: 0.6,
      gradient: 'radial-gradient(circle, rgba(82, 196, 26, 0.4), transparent)'
    },
    
    // Particle animation
    particle: {
      opacityKeyframes: [1, 1, 0],
      scaleKeyframes: [0, 1, 0.5],
      rotationMax: 720,
    }
  }
}

export default componentAnimationConfig

