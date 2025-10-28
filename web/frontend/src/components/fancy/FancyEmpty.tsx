/**
 * FancyEmpty - Enhanced Empty State with SVG Illustration
 * 
 * Features:
 * - Animated SVG illustration
 * - Friendly messaging
 * - CTA button with hover effect
 * - Floating animation
 */

import React from 'react'
import { Button } from 'antd'
import { motion } from 'framer-motion'
import { RocketOutlined } from '@ant-design/icons'
import { componentAnimationConfig } from '../../config/animation_config'

interface FancyEmptyProps {
  title: string
  description: string
  actionText?: string
  onAction?: () => void
  type?: 'no-data' | 'no-results' | 'error'
}

export const FancyEmpty: React.FC<FancyEmptyProps> = ({
  title,
  description,
  actionText,
  onAction,
  type = 'no-data'
}) => {
  const config = componentAnimationConfig.emptyState
  const svgConfig = config.svg
  const styleConfig = config.style
  
  // SVG Illustration
  const IllustrationSVG = () => (
    <svg width={svgConfig.width} height={svgConfig.height} viewBox="0 0 200 200" fill="none">
      {/* Animated circle */}
      <motion.circle
        cx="100"
        cy="100"
        r={svgConfig.circleRadius}
        stroke={svgConfig.circleStroke}
        strokeWidth={svgConfig.circleStrokeWidth}
        strokeDasharray={svgConfig.circleDashArray}
        fill="none"
        initial={{ rotate: 0 }}
        animate={{ rotate: 360 }}
        transition={{
          duration: svgConfig.circleRotationDuration,
          repeat: Infinity,
          ease: 'linear'
        }}
      />
      
      {/* Center icon group */}
      <motion.g
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{
          delay: 0.2,
          type: 'spring',
          stiffness: 200,
          damping: 15
        }}
      >
        {/* Folder/Document icon */}
        <rect x="70" y="85" width="60" height="45" rx="4" fill="#91caff" opacity="0.8" />
        <path d="M70 85 L70 80 Q70 75 75 75 L95 75 L100 80 L125 80 Q130 80 130 85 Z" fill="#69b1ff" />
        
        {/* Search magnifier */}
        <motion.g
          animate={{
            x: [0, 3, 0],
            y: [0, -3, 0]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut'
          }}
        >
          <circle cx="125" cy="125" r="12" fill="none" stroke="#1677ff" strokeWidth="2.5" />
          <line x1="133" y1="133" x2="143" y2="143" stroke="#1677ff" strokeWidth="2.5" strokeLinecap="round" />
        </motion.g>
      </motion.g>
      
       {/* Floating dots decoration */}
       {[...Array(svgConfig.dotCount)].map((_, i) => (
         <motion.circle
           key={i}
           cx={60 + i * 20}
           cy={40}
           r={svgConfig.dotRadius}
           fill={svgConfig.dotFill}
           opacity={svgConfig.dotOpacity}
           animate={{
             y: [0, svgConfig.dotFloatDistance, 0],
             opacity: [svgConfig.dotOpacity, svgConfig.dotOpacity * 2, svgConfig.dotOpacity]
           }}
           transition={{
             duration: svgConfig.dotFloatDuration,
             repeat: Infinity,
             delay: i * svgConfig.dotStaggerDelay,
             ease: 'easeInOut'
           }}
         />
       ))}
    </svg>
  )
  
   return (
     <motion.div
       initial={config.animation.initial}
       animate={config.animation.animate}
       transition={config.animation.transition}
       style={{
         padding: styleConfig.padding,
         textAlign: 'center',
         maxWidth: styleConfig.maxWidth,
         margin: '0 auto'
       }}
     >
       {/* SVG illustration with float animation */}
       <motion.div
         animate={config.illustrationFloat.animate}
         transition={{
           ...config.illustrationFloat.transition,
           repeat: Infinity
         }}
       >
         <IllustrationSVG />
       </motion.div>
       
       {/* Title */}
       <h2 style={{
         marginTop: styleConfig.titleMarginTop,
         marginBottom: styleConfig.titleMarginBottom,
         fontSize: styleConfig.titleFontSize,
         fontWeight: styleConfig.titleFontWeight,
         color: styleConfig.titleColor,
         lineHeight: styleConfig.titleLineHeight
       }}>
         {title}
       </h2>
       
       {/* Description */}
       <p style={{
         color: styleConfig.descriptionColor,
         fontSize: styleConfig.descriptionFontSize,
         lineHeight: styleConfig.descriptionLineHeight,
         marginBottom: styleConfig.descriptionMarginBottom,
         maxWidth: styleConfig.descriptionMaxWidth,
         margin: `0 auto ${styleConfig.descriptionMarginBottom}px`
       }}>
         {description}
       </p>
       
       {/* CTA Button */}
       {actionText && onAction && (
         <motion.div
           whileHover={config.buttonHover}
           whileTap={config.buttonTap}
         >
           <Button
             type="primary"
             size="large"
             icon={<RocketOutlined />}
             onClick={onAction}
             style={{
               borderRadius: styleConfig.buttonBorderRadius,
               height: styleConfig.buttonHeight,
               padding: styleConfig.buttonPadding,
               fontSize: styleConfig.buttonFontSize,
               fontWeight: styleConfig.buttonFontWeight,
               boxShadow: styleConfig.buttonShadow,
               background: `linear-gradient(135deg, ${styleConfig.buttonGradient[0]}, ${styleConfig.buttonGradient[1]})`,
               border: 'none'
             }}
           >
             {actionText}
           </Button>
         </motion.div>
       )}
     </motion.div>
   )
 }

export default FancyEmpty

