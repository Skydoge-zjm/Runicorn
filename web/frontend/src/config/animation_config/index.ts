/**
 * Animation Configuration Entry Point
 * 
 * Centralized exports for all animation configs
 */

// Import all configs
import commonConfig, { pageTransitionVariants, staggerContainerVariants, staggerItemVariants } from './common'
import experimentsConfig from './experiments'
import runDetailConfig from './run_detail'
import artifactsConfig from './artifacts'
import remoteConfig from './remote'
import componentConfig from './components'
import colorCfg, { createGradient, createRadialGradient } from './colors'

// Re-export with consistent names
export const animationConfig = commonConfig
export const experimentsPageConfig = experimentsConfig
export const runDetailPageConfig = runDetailConfig
export const artifactsPageConfig = artifactsConfig
export const remotePageConfig = remoteConfig
export const componentAnimationConfig = componentConfig
export const colorConfig = colorCfg

export { 
  pageTransitionVariants, 
  staggerContainerVariants, 
  staggerItemVariants,
  createGradient,
  createRadialGradient
}

// Also export as defaults for backward compatibility
export default {
  animationConfig,
  experimentsPageConfig,
  runDetailPageConfig,
  artifactsPageConfig,
  remotePageConfig,
  componentAnimationConfig,
  colorConfig
}

