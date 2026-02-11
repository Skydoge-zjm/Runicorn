/**
 * PageTransition - Page Route Transition Animations
 * 
 * Features:
 * - Smooth page enter/exit transitions
 * - Stagger children animation
 * - Configurable animation variants
 * 
 * Note: Simplified to avoid animation conflicts with page unmounting
 */

import { motion, AnimatePresence } from 'framer-motion'
import { useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

export const PageTransition = ({ children }: { children: ReactNode }) => {
  const location = useLocation()
  
  return (
    <AnimatePresence mode="sync" initial={false}>
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.15 }}
        style={{ 
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
          overflow: 'hidden',
        }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}

/**
 * StaggerContainer - Container for staggered children animations
 */
export const StaggerContainer: React.FC<{ 
  children: ReactNode
  staggerDelay?: number
}> = ({ children, staggerDelay = 0.08 }) => {
  return (
    <motion.div
      variants={{
        animate: {
          transition: {
            staggerChildren: staggerDelay
          }
        }
      }}
      initial="initial"
      animate="animate"
    >
      {children}
    </motion.div>
  )
}

/**
 * StaggerItem - Child item for stagger animation
 */
export const StaggerItem: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <motion.div
      variants={{
        initial: { opacity: 0, y: 20 },
        animate: {
          opacity: 1,
          y: 0,
          transition: {
            duration: 0.5,
            ease: [0.25, 0.1, 0.25, 1] as const
          }
        }
      }}
    >
      {children}
    </motion.div>
  )
}

export default PageTransition

