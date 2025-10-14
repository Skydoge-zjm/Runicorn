/**
 * Logger Utility
 * 
 * Provides conditional logging that only outputs in development mode.
 * In production builds, console statements are automatically stripped.
 */

const isDev = import.meta.env.DEV

export const logger = {
  log: (...args: any[]) => {
    if (isDev) console.log(...args)
  },
  
  error: (...args: any[]) => {
    if (isDev) console.error(...args)
  },
  
  warn: (...args: any[]) => {
    if (isDev) console.warn(...args)
  },
  
  info: (...args: any[]) => {
    if (isDev) console.info(...args)
  },
  
  debug: (...args: any[]) => {
    if (isDev) console.debug(...args)
  },
  
  table: (data: any) => {
    if (isDev) console.table(data)
  },
}

export default logger
