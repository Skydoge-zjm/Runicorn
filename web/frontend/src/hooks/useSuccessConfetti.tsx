/**
 * useSuccessConfetti - Success Celebration Animation Hook
 * 
 * Creates a confetti explosion effect for success feedback
 * Lightweight and performant
 */

import { useState } from 'react'
import { motion } from 'framer-motion'

export const useSuccessConfetti = () => {
  const [show, setShow] = useState(false)
  
  const trigger = () => {
    setShow(true)
    setTimeout(() => setShow(false), 2000)
  }
  
  const ConfettiComponent = show ? (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      pointerEvents: 'none',
      zIndex: 9999
    }}>
      {/* Generate 20 confetti particles */}
      {[...Array(20)].map((_, i) => {
        const colors = ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#13c2c2']
        const startX = typeof window !== 'undefined' ? window.innerWidth / 2 : 500
        const startY = typeof window !== 'undefined' ? window.innerHeight / 2 : 300
        const angle = (i / 20) * 2 * Math.PI
        const distance = 200 + Math.random() * 200
        const endX = startX + Math.cos(angle) * distance
        const endY = startY + Math.sin(angle) * distance - 200
        
        return (
          <motion.div
            key={i}
            style={{
              position: 'absolute',
              left: startX,
              top: startY,
              width: 8 + Math.random() * 8,
              height: 8 + Math.random() * 8,
              background: colors[i % colors.length],
              borderRadius: '50%'
            }}
            initial={{
              x: 0,
              y: 0,
              opacity: 1,
              scale: 0
            }}
            animate={{
              x: endX - startX,
              y: endY - startY,
              opacity: [1, 1, 0],
              scale: [0, 1, 0.5],
              rotate: Math.random() * 720
            }}
            transition={{
              duration: 1.5,
              ease: [0.25, 0.1, 0.25, 1]
            }}
          />
        )
      })}
      
      {/* Center burst effect */}
      <motion.div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          width: 100,
          height: 100,
          marginLeft: -50,
          marginTop: -50,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(82, 196, 26, 0.4), transparent)'
        }}
        initial={{ scale: 0, opacity: 1 }}
        animate={{ scale: 3, opacity: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      />
    </div>
  ) : null
  
  return { trigger, ConfettiComponent }
}

export default useSuccessConfetti

