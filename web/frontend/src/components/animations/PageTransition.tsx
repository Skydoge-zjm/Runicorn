/**
 * PageTransition - Page Route Transition Animations
 * 
 * Features:
 * - Smooth page enter/exit transitions
 * - Stagger children animation
 * - Configurable animation variants
 */

import { motion, AnimatePresence } from 'framer-motion'
import { useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

const pageVariants = {
  initial: {
    opacity: 0,
    y: 24,
    scale: 0.96
  },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.5,
      ease: [0.25, 0.1, 0.25, 1] as const,
      when: 'beforeChildren',
      staggerChildren: 0.1
    }
  },
  exit: {
    opacity: 0,
    y: -24,
    scale: 0.96,
    transition: {
      duration: 0.3,
      ease: [0.25, 0.1, 0.25, 1] as const
    }
  }
}

export const PageTransition = ({ children }: { children: ReactNode }) => {
  const location = useLocation()
  
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        variants={pageVariants}
        initial="initial"
        animate="animate"
        exit="exit"
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

