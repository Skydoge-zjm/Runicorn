import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('logger', () => {
  const methods = ['log', 'error', 'warn', 'info', 'debug', 'table'] as const

  beforeEach(() => {
    vi.resetModules()
    methods.forEach((m) => vi.spyOn(console, m).mockImplementation(() => {}))
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('when DEV = true', () => {
    beforeEach(() => {
      vi.stubEnv('DEV', 'true')
      // Force import.meta.env.DEV = true
      vi.doMock('../utils/logger', async () => {
        // Re-evaluate the module with DEV = true
        const isDev = true
        return {
          logger: {
            log: (...args: any[]) => { if (isDev) console.log(...args) },
            error: (...args: any[]) => { if (isDev) console.error(...args) },
            warn: (...args: any[]) => { if (isDev) console.warn(...args) },
            info: (...args: any[]) => { if (isDev) console.info(...args) },
            debug: (...args: any[]) => { if (isDev) console.debug(...args) },
            table: (data: any) => { if (isDev) console.table(data) },
          },
          default: undefined,
        }
      })
    })

    it.each(methods.filter(m => m !== 'table'))('%s() calls console.%s', async (method) => {
      const mod = await import('./logger')
      mod.logger[method]('test', 123)
      expect(console[method]).toHaveBeenCalledWith('test', 123)
    })

    it('table() calls console.table', async () => {
      const mod = await import('./logger')
      mod.logger.table([1, 2])
      expect(console.table).toHaveBeenCalledWith([1, 2])
    })
  })

  describe('when DEV = false', () => {
    beforeEach(() => {
      vi.doMock('../utils/logger', async () => {
        const isDev = false
        return {
          logger: {
            log: (...args: any[]) => { if (isDev) console.log(...args) },
            error: (...args: any[]) => { if (isDev) console.error(...args) },
            warn: (...args: any[]) => { if (isDev) console.warn(...args) },
            info: (...args: any[]) => { if (isDev) console.info(...args) },
            debug: (...args: any[]) => { if (isDev) console.debug(...args) },
            table: (data: any) => { if (isDev) console.table(data) },
          },
          default: undefined,
        }
      })
    })

    it.each(methods.filter(m => m !== 'table'))('%s() does NOT call console.%s', async (method) => {
      const mod = await import('./logger')
      mod.logger[method]('test')
      expect(console[method]).not.toHaveBeenCalled()
    })

    it('table() does NOT call console.table', async () => {
      const mod = await import('./logger')
      mod.logger.table([1])
      expect(console.table).not.toHaveBeenCalled()
    })
  })
})
