import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  formatFileSize,
  formatBytes,
  formatTimestamp,
  formatDuration,
  formatRelativeTime,
  formatPercent,
  formatNumber,
  truncateText,
  formatRunId,
} from './format'

// ── formatFileSize / formatBytes ──

describe('formatFileSize', () => {
  it('returns "0 B" for 0 bytes', () => {
    expect(formatFileSize(0)).toBe('0 B')
  })

  it('returns bytes below 1 KB', () => {
    expect(formatFileSize(1023)).toBe('1023 B')
  })

  it('returns "1 KB" for 1024 bytes', () => {
    expect(formatFileSize(1024)).toBe('1 KB')
  })

  it('returns "1 MB" for 1048576 bytes', () => {
    expect(formatFileSize(1048576)).toBe('1 MB')
  })

  it('returns "1 TB" for 1099511627776 bytes', () => {
    expect(formatFileSize(1099511627776)).toBe('1 TB')
  })

  it('handles negative numbers defensively', () => {
    // Math.log of negative → NaN → sizes[NaN] → undefined; just ensure no crash
    const result = formatFileSize(-100)
    expect(typeof result).toBe('string')
  })
})

describe('formatBytes', () => {
  it('is an alias for formatFileSize', () => {
    expect(formatBytes).toBe(formatFileSize)
  })
})

// ── formatTimestamp ──

describe('formatTimestamp', () => {
  it('returns "-" for 0', () => {
    expect(formatTimestamp(0)).toBe('-')
  })

  it('returns "-" for NaN', () => {
    expect(formatTimestamp(NaN)).toBe('-')
  })

  it('auto-converts seconds-level (10-digit) timestamp to ms', () => {
    const ts = 1700000000 // 10 digits
    const result = formatTimestamp(ts)
    expect(result).toMatch(/\d{2}/)
  })

  it('uses millisecond timestamp directly (13 digits)', () => {
    const ts = 1700000000000
    const result = formatTimestamp(ts)
    expect(result).toMatch(/\d{2}/)
  })

  it('output contains year/month/day/hour/minute/second parts', () => {
    const ts = 1700000000000
    const result = formatTimestamp(ts)
    // toLocaleString('en-US', ...) → "MM/DD/YYYY, HH:mm:ss"
    expect(result).toMatch(/\d+.*\d+.*\d+.*\d+:\d+:\d+/)
  })
})

// ── formatDuration ──

describe('formatDuration', () => {
  it('returns "0s" for 0', () => {
    expect(formatDuration(0)).toBe('0s')
  })

  it('returns "0s" for negative values', () => {
    expect(formatDuration(-1000)).toBe('0s')
  })

  it('formats pure seconds', () => {
    expect(formatDuration(5000)).toBe('5s')
  })

  it('formats minutes and seconds', () => {
    expect(formatDuration(65000)).toBe('1m 5s')
  })

  it('formats hours and minutes', () => {
    expect(formatDuration(3661000)).toBe('1h 1m')
  })

  it('formats days and hours', () => {
    expect(formatDuration(90061000)).toBe('1d 1h')
  })
})

// ── formatRelativeTime ──

describe('formatRelativeTime', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns "-" for 0', () => {
    expect(formatRelativeTime(0)).toBe('-')
  })

  it('returns "-" for NaN', () => {
    expect(formatRelativeTime(NaN)).toBe('-')
  })

  it('returns relative string for recent time (< 60s ago)', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-01-15T12:00:30Z'))
    const ts = new Date('2024-01-15T12:00:00Z').getTime()
    const result = formatRelativeTime(ts)
    // Intl.RelativeTimeFormat with numeric: 'auto' → "30 seconds ago" or "now"
    expect(result.toLowerCase()).toMatch(/second|now/)
    vi.useRealTimers()
  })

  it('returns relative string for 5 minutes ago', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-01-15T12:05:00Z'))
    const ts = new Date('2024-01-15T12:00:00Z').getTime()
    const result = formatRelativeTime(ts)
    expect(result).toMatch(/5/)
    expect(result.toLowerCase()).toMatch(/minute/)
  })

  it('returns relative string for 3 hours ago', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-01-15T15:00:00Z'))
    const ts = new Date('2024-01-15T12:00:00Z').getTime()
    const result = formatRelativeTime(ts)
    expect(result).toMatch(/3/)
    expect(result.toLowerCase()).toMatch(/hour/)
  })

  it('returns relative string for 2 days ago', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-01-17T12:00:00Z'))
    const ts = new Date('2024-01-15T12:00:00Z').getTime()
    const result = formatRelativeTime(ts)
    expect(result).toMatch(/2/)
    expect(result.toLowerCase()).toMatch(/day/)
  })

  it('falls back to formatTimestamp for > 30 days', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-03-15T12:00:00Z'))
    const ts = new Date('2024-01-15T12:00:00Z').getTime()
    const result = formatRelativeTime(ts)
    // Should be an absolute date string, not relative
    expect(result).toMatch(/\d+/)
    expect(result.toLowerCase()).not.toMatch(/day|ago/)
  })

  it('falls back to formatTimestamp for future timestamps', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-01-15T12:00:00Z'))
    const ts = new Date('2024-02-15T12:00:00Z').getTime()
    const result = formatRelativeTime(ts)
    expect(result).toMatch(/\d+/)
  })
})

// ── formatPercent ──

describe('formatPercent', () => {
  it('formats 0.1234 to "12.34%"', () => {
    expect(formatPercent(0.1234)).toBe('12.34%')
  })

  it('returns "-" for NaN', () => {
    expect(formatPercent(NaN)).toBe('-')
  })

  it('respects custom precision', () => {
    expect(formatPercent(0.1234, 1)).toBe('12.3%')
  })
})

// ── formatNumber ──

describe('formatNumber', () => {
  it('formats number with thousand separators', () => {
    const result = formatNumber(1234567)
    expect(result).toContain(',')
  })

  it('returns "-" for NaN', () => {
    expect(formatNumber(NaN)).toBe('-')
  })

  it('respects precision parameter', () => {
    const result = formatNumber(1234.5678, 2)
    expect(result).toContain('1,234.57')
  })
})

// ── truncateText ──

describe('truncateText', () => {
  it('returns empty string for falsy input', () => {
    expect(truncateText('')).toBe('')
  })

  it('returns original text if shorter than maxLength', () => {
    expect(truncateText('hello', 10)).toBe('hello')
  })

  it('truncates text with ellipsis if longer than maxLength', () => {
    const result = truncateText('abcdefghijklmno', 10)
    expect(result).toBe('abcdefg...')
    expect(result.length).toBe(10)
  })
})

// ── formatRunId ──

describe('formatRunId', () => {
  it('returns "-" for empty string', () => {
    expect(formatRunId('')).toBe('-')
  })

  it('returns original if <= 8 chars', () => {
    expect(formatRunId('abcd1234')).toBe('abcd1234')
  })

  it('truncates to 8 chars with ellipsis', () => {
    expect(formatRunId('abcdefghijklmnop')).toBe('abcdefgh...')
  })
})
