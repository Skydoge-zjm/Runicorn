/**
 * FancyStatCard - Gradient Statistics Card with Count Animation
 * 
 * Features:
 * - Gradient background
 * - Large semi-transparent icon
 * - Count-up number animation
 * - Hover lift effect
 * - Shimmer animation
 * - Pulse effect for active states
 */

import React, { useEffect } from 'react'
import { Card } from 'antd'
import { motion, useMotionValue, useTransform, animate } from 'framer-motion'
import type { ReactNode } from 'react'
import { componentAnimationConfig } from '../../config/animation_config'

interface FancyStatCardProps {
  title: string
  value: number
  icon: ReactNode
  gradientColors: [string, string]
  delay?: number
  pulse?: boolean
  onClick?: () => void
  formattedValue?: string | ReactNode  // Custom formatted display (overrides animated number)
  subtitle?: string  // Additional subtitle text
}

export const FancyStatCard: React.FC<FancyStatCardProps> = ({
  title,
  value,
  icon,
  gradientColors: [color1, color2],
  delay = 0,
  pulse = false,
  onClick,
  formattedValue,
  subtitle
}) => {
  const config = componentAnimationConfig.fancyStatCard
  
  // Number count-up animation using smooth tween (no bounce/overshoot)
  const motionValue = useMotionValue(0)
  
  const display = useTransform(motionValue, (latest) => {
    return Math.floor(latest).toLocaleString()
  })
  
  useEffect(() => {
    // Animate from current value to target value with easeOut
    const controls = animate(motionValue, value, {
      duration: 0.5,           // Smooth 0.8s animation
      ease: [0, 0.2, 0.5, 1],    // easeOut curve - fast start, smooth stop
    })
    
    return controls.stop
  }, [value, motionValue])
  
  const entranceTransition = {
    ...config.entrance.transition,
    delay
  }
  
  return (
    <motion.div
      initial={config.entrance.initial}
      animate={config.entrance.animate}
      transition={entranceTransition}
      whileHover={config.hover}
      whileTap={onClick ? config.tap : {}}
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default', height: '100%' }}
    >
      <Card
        bordered={false}
        style={{
          background: `linear-gradient(135deg, ${color1}, ${color2})`,
          borderRadius: config.style.borderRadius,
          overflow: 'hidden',
          position: 'relative',
          height: '100%',
          minHeight: config.style.minHeight,
          boxShadow: config.style.boxShadow,
        }}
        bodyStyle={{
          padding: 24,
          position: 'relative',
          zIndex: 1
        }}
      >
        {/* Background decorative icon */}
        <div style={{
          position: 'absolute',
          right: config.style.iconPosition.right,
          top: config.style.iconPosition.top,
          fontSize: config.style.iconSize,
          opacity: config.style.iconOpacity,
          color: '#fff',
          pointerEvents: 'none'
        }}>
          {icon}
        </div>
        
        {/* Pulse glow effect for active states */}
        {pulse && (
          <motion.div
            style={{
              position: 'absolute',
              top: '-50%',
              right: '-50%',
              width: '200%',
              height: '200%',
              background: 'radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%)',
              pointerEvents: 'none'
            }}
            animate={config.pulse.animate}
            transition={{
              ...config.pulse.transition,
              repeat: Infinity
            }}
          />
        )}
        
        {/* Main content */}
        <div style={{ position: 'relative' }}>
          {/* Title */}
          <div style={{
            color: config.style.titleColor,
            fontSize: config.style.titleFontSize,
            fontWeight: config.style.titleFontWeight,
            marginBottom: config.style.titleMarginBottom,
            letterSpacing: config.style.titleLetterSpacing
          }}>
            {title}
          </div>
          
          {/* Animated value */}
          <div style={{
            color: config.style.valueColor,
            fontSize: config.style.valueFontSize,
            fontWeight: config.style.valueFontWeight,
            lineHeight: 1,
            fontVariantNumeric: 'tabular-nums',
            textShadow: config.style.valueTextShadow
          }}>
            {formattedValue !== undefined ? (
              <span>{formattedValue}</span>
            ) : (
              <motion.span>{display}</motion.span>
            )}
          </div>
          
          {/* Optional subtitle */}
          {subtitle && (
            <div style={{
              color: 'rgba(255, 255, 255, 0.85)',
              fontSize: 12,
              marginTop: 8,
              fontWeight: 400
            }}>
              {subtitle}
            </div>
          )}
        </div>
        
        {/* Shimmer effect */}
        <motion.div
          style={{
            position: 'absolute',
            top: 0,
            left: '-100%',
            width: '100%',
            height: '100%',
            background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
            pointerEvents: 'none'
          }}
          animate={config.shimmer.animate}
          transition={{
            ...config.shimmer.transition,
            repeat: Infinity
          }}
        />
      </Card>
    </motion.div>
  )
}

export default FancyStatCard

