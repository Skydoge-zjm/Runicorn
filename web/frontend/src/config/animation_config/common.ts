/**
 * Common Animation Configuration
 * 
 * Centralized animation parameters for consistent UI/UX across the application.
 * This is the "preset library" that component-specific configs can reference.
 * 
 * Architecture:
 * - common.ts (this file) - Reusable animation presets
 * - components.ts - Component-specific overrides
 * - {page}.ts - Page-specific configurations
 * 
 * All timing, easing, and animation values are defined here for easy tuning.
 */

export const animationConfig = {
  // ==================== ANIMATION DURATIONS ====================
  // All durations are in seconds (not milliseconds)
  // Guidelines:
  // - fast (0.15-0.25s): Micro-interactions, instant feedback
  // - normal (0.3-0.4s): Standard transitions, most UI changes
  // - medium (0.5-0.7s): Emphasized transitions, page loads
  // - slow (0.8-1.2s): Dramatic effects, major state changes
  durations: {
    fast: 0.2,      // Quick feedback (hover effects, ripples)
    normal: 0.3,    // Standard transitions (fade in/out, slides)
    medium: 0.5,    // Emphasized animations (modal opens, page transitions)
    slow: 0.8,      // Slow, dramatic effects (loading screens, celebrations)
    
    // ===== Specific Use Cases =====
    pageTransition: 0.5,   // Time for page enter animation
    pageExit: 0.3,         // Time for page exit (faster than enter)
    cardEnter: 0.6,        // Card/list item entrance
    buttonFeedback: 0.2,   // Button press/hover feedback
    modalTransition: 0.3,  // Modal/dialog open/close
    tooltipDelay: 0.5,     // Delay before showing tooltip
  },
  
  // ==================== EASING FUNCTIONS ====================
  // Controls the acceleration curve of animations (how they speed up/slow down)
  // Format: [x1, y1, x2, y2] - cubic-bezier control points
  // Tool for visualizing: https://cubic-bezier.com/
  easings: {
    // ===== Cubic Bezier Easings =====
    // Standard easings based on Material Design and modern UI patterns
    
    default: [0.25, 0.1, 0.25, 1] as [number, number, number, number],
    // Default ease - smooth acceleration and deceleration
    // Use for: Most animations, natural feeling transitions
    
    easeIn: [0.4, 0, 1, 1] as [number, number, number, number],
    // Slow start, fast end - elements leaving the screen
    // Use for: Exit animations, elements moving away
    
    easeOut: [0, 0, 0.2, 1] as [number, number, number, number],
    // Fast start, slow end - elements entering the screen
    // Use for: Enter animations, appearing elements
    
    easeInOut: [0.4, 0, 0.2, 1] as [number, number, number, number],
    // Slow start and end, fast middle - symmetrical motion
    // Use for: Move between states, position changes
    
    // ===== Spring Physics Presets =====
    // Spring animations simulate real-world physics for natural-feeling motion
    // Unlike cubic-bezier, springs can overshoot and bounce back
    // 
    // Parameters explained:
    // - stiffness: Spring tension (50-300 typical range)
    //   * Low (50-100): Slow, gentle motion
    //   * Medium (100-200): Balanced, natural feel
    //   * High (200-300): Fast, snappy response
    // 
    // - damping: Resistance/friction (10-50 typical range)
    //   * Low (10-20): Pronounced bounce, playful
    //   * Medium (25-35): Subtle bounce, natural
    //   * High (35-50): No overshoot, smooth deceleration
    // 
    // Formula: Higher stiffness/damping ratio = more bounce
    
    spring: {
      stiffness: 100,   // Balanced spring - moderate speed, slight bounce
      damping: 30       // Medium damping - minimal oscillation, natural feel
      // Use for: General purpose animations, modal opens, card flips
      // Feel: Natural, versatile - works for most UI elements
    },
    
    springBouncy: {
      stiffness: 260,   // Stiff spring - very fast, energetic motion
      damping: 20       // Low damping - noticeable bounce/overshoot, playful feel
      // Use for: Success animations, celebration effects, attention-grabbing
      // Feel: Energetic, playful - adds personality and delight
      // Example: Badge appears, success confetti, notification pop
    },
    
    springGentle: {
      stiffness: 80,    // Soft spring - slower, more gradual motion
      damping: 25       // Medium-low damping - smooth with subtle bounce, relaxed feel
      // Use for: Large modals, page transitions, non-urgent notifications
      // Feel: Calm, relaxed - doesn't demand immediate attention
      // Example: Settings panel slides in, large image gallery
    }
  },
  
  // ==================== STAGGER DELAYS ====================
  // Delay between animating multiple items in sequence (in seconds)
  // Creates cascading "wave" effect when animating lists/grids
  // Formula: total_time = stagger_delay × number_of_items
  stagger: {
    fast: 0.05,       // 50ms - Quick succession (20 items/second)
                      // Use for: Small UI elements, tight lists, badges
    
    normal: 0.08,     // 80ms - Standard rhythm (12.5 items/second)
                      // Use for: Most lists, navigation items, form fields
    
    slow: 0.1,        // 100ms - Noticeable delay (10 items/second)
                      // Use for: Large cards, emphasized content, gallery items
    
    cards: 0.1,       // 100ms - For card grids specifically
    listItems: 0.05,  // 50ms - For dense lists/tables
  },
  
  // ==================== TRANSFORM VALUES ====================
  // Position, scale, and other transform parameters (pixels or multipliers)
  transforms: {
    // ===== Slide Distances (Y-axis movement) =====
    slideDistance: 24,        // Standard slide for entering elements (24px)
                              // Use for: List items, cards, modals
    
    slideDistanceLarge: 40,   // Larger slide for dramatic entrances (40px)
                              // Use for: Page transitions, hero sections
    
    // ===== Scale Values (multipliers) =====
    scaleHover: 1.03,        // Subtle grow on hover (3% larger)
                             // Use for: Cards, buttons, interactive elements
    
    scaleActive: 0.98,       // Slight shrink when pressed (2% smaller)
                             // Use for: Buttons, clickable items - feedback
    
    scaleEnter: 0.96,        // Initial scale for entrance (96% of final size)
                             // Use for: Pop-in effects, appearing elements
    
    // ===== Specific Transform Values =====
    cardHoverLift: -6,       // Negative Y (upward) on hover (6px up)
                             // Use for: Card hover states, lifted appearance
    
    rowHoverLift: -1,        // Subtle lift for table rows (1px up)
                             // Use for: Table rows, list items - minimal feedback
    
    buttonHoverScale: 1.05,  // Button grows 5% on hover
                             // Use for: Primary buttons, call-to-action elements
  },
  
  // ==================== OPACITY VALUES ====================
  // Transparency levels (0 = invisible, 1 = fully visible)
  // Consistent opacity levels prevent "magical numbers" in code
  opacity: {
    hidden: 0,      // Completely invisible (0%)
                    // Use for: Initial state of fade-in animations
    
    visible: 1,     // Fully visible (100%)
                    // Use for: Final state of animations, normal content
    
    dimmed: 0.7,    // Slightly transparent (70%)
                    // Use for: Disabled states, background content, overlays
    
    subtle: 0.4,    // Very transparent (40%)
                    // Use for: Placeholder text, decorative elements
  },
  
  // ==================== ANIMATION DELAYS ====================
  // Waiting periods before animations start (in seconds)
  delays: {
    pageContent: 0.2,      // Delay before page content animates in
                           // Allows page structure to render first
    
    staggerBase: 0.1,      // Base delay for staggered animations
                           // Can be multiplied by item index
    
    shimmerRepeat: 5,      // Seconds between shimmer effect repeats
                           // For loading skeletons, highlight effects
    
    confettiDuration: 2,   // How long confetti animation lasts
                           // Success celebrations, achievements
  }
}

// ==================== FRAMER MOTION VARIANTS ====================
// Pre-built animation variants for common use cases
// These use the config values above for consistency
// 
// Usage:
// import { pageTransitionVariants } from './common'
// <motion.div variants={pageTransitionVariants} initial="initial" animate="animate" />

/**
 * Page Transition Variants
 * 
 * Standard page entrance/exit animation with slide and fade
 * - Enters from below with fade in
 * - Exits upward with fade out
 * - Automatically animates children with stagger
 * 
 * Usage:
 * <motion.div
 *   variants={pageTransitionVariants}
 *   initial="initial"
 *   animate="animate"
 *   exit="exit"
 * >
 *   {content}
 * </motion.div>
 */
export const pageTransitionVariants = {
  initial: {
    opacity: animationConfig.opacity.hidden,        // Start invisible
    y: animationConfig.transforms.slideDistance,    // Start 24px below
    scale: animationConfig.transforms.scaleEnter    // Start slightly smaller (96%)
  },
  animate: {
    opacity: animationConfig.opacity.visible,       // Fade to visible
    y: 0,                                           // Slide to final position
    scale: 1,                                       // Scale to normal size
    transition: {
      duration: animationConfig.durations.pageTransition,  // 0.5s animation
      ease: animationConfig.easings.default,               // Smooth easing
      when: 'beforeChildren',                              // Parent animates first
      staggerChildren: animationConfig.stagger.normal      // Then children with 0.08s delay
    }
  },
  exit: {
    opacity: animationConfig.opacity.hidden,        // Fade out
    y: -animationConfig.transforms.slideDistance,   // Slide up 24px (opposite of enter)
    scale: animationConfig.transforms.scaleEnter,   // Shrink slightly
    transition: {
      duration: animationConfig.durations.pageExit,  // Faster exit (0.3s)
      ease: animationConfig.easings.default
    }
  }
}

/**
 * Stagger Container Variants
 * 
 * Container that triggers staggered animations for its children
 * No visual animation on the container itself
 * 
 * Usage:
 * <motion.div variants={staggerContainerVariants} initial="initial" animate="animate">
 *   <motion.div variants={staggerItemVariants}>Item 1</motion.div>
 *   <motion.div variants={staggerItemVariants}>Item 2</motion.div>
 *   <motion.div variants={staggerItemVariants}>Item 3</motion.div>
 * </motion.div>
 * 
 * Result: Items animate in sequence with 0.1s delay between each
 */
export const staggerContainerVariants = {
  animate: {
    transition: {
      staggerChildren: animationConfig.stagger.cards  // 0.1s delay between children
    }
  }
}

/**
 * Stagger Item Variants
 * 
 * Individual items in a staggered list/grid
 * Fades in from below
 * 
 * Must be used inside a staggerContainerVariants parent
 */
export const staggerItemVariants = {
  initial: { 
    opacity: animationConfig.opacity.hidden,         // Start invisible
    y: animationConfig.transforms.slideDistance      // Start 24px below
  },
  animate: {
    opacity: animationConfig.opacity.visible,        // Fade to visible
    y: 0,                                            // Slide to position
    transition: {
      duration: animationConfig.durations.medium,    // 0.5s per item
      ease: animationConfig.easings.default
    }
  }
}

export default animationConfig

