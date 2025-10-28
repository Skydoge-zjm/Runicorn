/**
 * ShimmerSkeleton - Shimmer Loading Effect
 * 
 * Modern loading placeholder with animated shimmer
 * More engaging than simple spinner
 */

import { motion } from 'framer-motion'

interface ShimmerSkeletonProps {
  width?: string | number
  height?: number
  borderRadius?: number
}

export const ShimmerSkeleton: React.FC<ShimmerSkeletonProps> = ({
  width = '100%',
  height = 20,
  borderRadius = 4
}) => {
  return (
    <div style={{
      width,
      height,
      backgroundColor: '#f0f0f0',
      borderRadius,
      overflow: 'hidden',
      position: 'relative'
    }}>
      <motion.div
        style={{
          position: 'absolute',
          top: 0,
          left: '-100%',
          width: '100%',
          height: '100%',
          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.9), transparent)',
        }}
        animate={{
          left: ['100%', '200%']
        }}
        transition={{
          duration: 1.2,
          repeat: Infinity,
          ease: 'linear'
        }}
      />
    </div>
  )
}

/**
 * FancyCardSkeleton - Skeleton for fancy stat cards
 */
export const FancyCardSkeleton: React.FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{
        padding: 24,
        borderRadius: 16,
        background: 'linear-gradient(135deg, #f5f5f5, #e8e8e8)',
        minHeight: 140
      }}
    >
      <ShimmerSkeleton width="60%" height={16} />
      <div style={{ marginTop: 16 }}>
        <ShimmerSkeleton width="80%" height={36} />
      </div>
    </motion.div>
  )
}

/**
 * FancyTableSkeleton - Skeleton for table rows
 */
export const FancyTableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => {
  return (
    <div style={{ padding: 24 }}>
      {[...Array(rows)].map((_, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: i * 0.05 }}
          style={{ marginBottom: 16 }}
        >
          <ShimmerSkeleton height={48} />
        </motion.div>
      ))}
    </div>
  )
}

export default ShimmerSkeleton

