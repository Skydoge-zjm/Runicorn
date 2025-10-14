/**
 * Common formatting utilities for the frontend
 */

/**
 * Format bytes to human readable format
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * Format bytes (alias for formatFileSize for compatibility)
 */
export const formatBytes = formatFileSize

/**
 * Format Unix timestamp to human readable date/time
 */
export function formatTimestamp(timestamp: number): string {
  if (!timestamp || timestamp === 0) return '-'
  
  // If timestamp is in seconds (10 digits), convert to milliseconds
  const ms = timestamp < 10000000000 ? timestamp * 1000 : timestamp
  
  const date = new Date(ms)
  
  // Check if date is valid
  if (isNaN(date.getTime())) return '-'
  
  // Format: YYYY-MM-DD HH:mm:ss
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

/**
 * Format duration in milliseconds to human readable format
 */
export function formatDuration(ms: number): string {
  if (!ms || ms <= 0) return '0s'
  
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) {
    const remainingHours = hours % 24
    return `${days}d ${remainingHours}h`
  }
  
  if (hours > 0) {
    const remainingMinutes = minutes % 60
    return `${hours}h ${remainingMinutes}m`
  }
  
  if (minutes > 0) {
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }
  
  return `${seconds}s`
}

/**
 * Format date to relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(timestamp: number): string {
  if (!timestamp || timestamp === 0) return '-'
  
  // If timestamp is in seconds, convert to milliseconds
  const ms = timestamp < 10000000000 ? timestamp * 1000 : timestamp
  const date = new Date(ms)
  
  if (isNaN(date.getTime())) return '-'
  
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  
  // If negative (future date), just show the date
  if (diffMs < 0) {
    return formatTimestamp(timestamp)
  }
  
  const seconds = Math.floor(diffMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 30) {
    return formatTimestamp(timestamp)
  }
  
  if (days > 0) {
    return `${days} day${days > 1 ? 's' : ''} ago`
  }
  
  if (hours > 0) {
    return `${hours} hour${hours > 1 ? 's' : ''} ago`
  }
  
  if (minutes > 0) {
    return `${minutes} minute${minutes > 1 ? 's' : ''} ago`
  }
  
  return 'just now'
}

/**
 * Format percentage value
 */
export function formatPercent(value: number, precision: number = 2): string {
  if (value === null || value === undefined || isNaN(value)) return '-'
  return `${(value * 100).toFixed(precision)}%`
}

/**
 * Format number with thousand separators
 */
export function formatNumber(value: number, precision?: number): string {
  if (value === null || value === undefined || isNaN(value)) return '-'
  
  if (precision !== undefined) {
    return value.toFixed(precision).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  }
  
  return value.toLocaleString('en-US')
}

/**
 * Truncate text with ellipsis
 */
export function truncateText(text: string, maxLength: number = 100): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 3) + '...'
}

/**
 * Format run ID (show first 8 characters)
 */
export function formatRunId(runId: string): string {
  if (!runId) return '-'
  return runId.length > 8 ? `${runId.substring(0, 8)}...` : runId
}
