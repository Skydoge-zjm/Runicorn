import { describe, it, expect } from 'vitest'
import {
  sanitizeFilename,
  suggestAssetDownloadFilename,
  isProbablyTextFilename,
} from './assetDownload'

// ── sanitizeFilename ──

describe('sanitizeFilename', () => {
  it('replaces backslashes and forward slashes with _', () => {
    expect(sanitizeFilename('a\\b/c')).toBe('a_b_c')
  })

  it('compresses multiple spaces into one', () => {
    expect(sanitizeFilename('a   b')).toBe('a b')
  })

  it('trims whitespace', () => {
    expect(sanitizeFilename('  hello  ')).toBe('hello')
  })

  it('returns empty string for empty input', () => {
    expect(sanitizeFilename('')).toBe('')
  })
})

// ── suggestAssetDownloadFilename ──

describe('suggestAssetDownloadFilename', () => {
  it('returns "code_snapshot.zip" for kind=code', () => {
    expect(suggestAssetDownloadFilename({ kind: 'code' })).toBe('code_snapshot.zip')
  })

  it('returns "config.json" for kind=config', () => {
    expect(suggestAssetDownloadFilename({ kind: 'config' })).toBe('config.json')
  })

  it('appends .zip when archive_path ends with .zip', () => {
    const asset = { kind: 'dataset', name: 'train', archive_path: '/data/train.zip' }
    expect(suggestAssetDownloadFilename(asset)).toBe('train.zip')
  })

  it('does not double .zip suffix', () => {
    const asset = { kind: 'dataset', name: 'train.zip', archive_path: '/data/train.zip' }
    expect(suggestAssetDownloadFilename(asset)).toBe('train.zip')
  })

  it('falls back to "asset" when no name or meta', () => {
    expect(suggestAssetDownloadFilename({ kind: 'dataset' })).toBe('asset')
  })

  it('prefers meta.name over asset.name', () => {
    const asset = { kind: 'dataset', name: 'fallback', meta: { name: 'preferred' } }
    expect(suggestAssetDownloadFilename(asset)).toBe('preferred')
  })
})

// ── isProbablyTextFilename ──

describe('isProbablyTextFilename', () => {
  it.each(['.py', '.json', '.yaml', '.yml', '.md', '.txt', '.csv', '.ts', '.js', '.html'])(
    'returns true for %s extension',
    (ext) => {
      expect(isProbablyTextFilename(`file${ext}`)).toBe(true)
    },
  )

  it.each(['.png', '.bin', '.exe', '.pdf', '.mp4'])(
    'returns false for %s extension',
    (ext) => {
      expect(isProbablyTextFilename(`file${ext}`)).toBe(false)
    },
  )

  it('returns false for empty string', () => {
    expect(isProbablyTextFilename('')).toBe(false)
  })

  it('is case insensitive', () => {
    expect(isProbablyTextFilename('file.JSON')).toBe(true)
    expect(isProbablyTextFilename('file.PY')).toBe(true)
  })
})
