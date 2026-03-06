import { describe, it, expect } from 'vitest'
import {
  buildAssetIdentity,
  assetIdentityToString,
  encodeAssetIdentity,
  decodeAssetIdentity,
  type AssetIdentity,
} from './assetIdentity'

// ── buildAssetIdentity ──

describe('buildAssetIdentity', () => {
  it('uses fingerprint when available', () => {
    const id = buildAssetIdentity({ kind: 'dataset', fingerprint: 'abc123' })
    expect(id).toEqual({ kind: 'dataset', idType: 'fingerprint', idValue: 'abc123' })
  })

  it('falls back to archive_path when no fingerprint', () => {
    const id = buildAssetIdentity({ kind: 'code', archive_path: '/data/snap.zip' })
    expect(id).toEqual({ kind: 'code', idType: 'archive_path', idValue: '/data/snap.zip' })
  })

  it('falls back to source_uri when no fingerprint or archive_path', () => {
    const id = buildAssetIdentity({ kind: 'pretrained', source_uri: 'https://model.bin' })
    expect(id).toEqual({ kind: 'pretrained', idType: 'source_uri', idValue: 'https://model.bin' })
  })

  it('falls back to name when nothing else available', () => {
    const id = buildAssetIdentity({ kind: 'output', name: 'my_output' })
    expect(id).toEqual({ kind: 'output', idType: 'name', idValue: 'my_output' })
  })

  it('returns idValue "-" when all fields are empty', () => {
    const id = buildAssetIdentity({ kind: 'custom' })
    expect(id).toEqual({ kind: 'custom', idType: 'name', idValue: '-' })
  })

  it('skips whitespace-only fingerprint', () => {
    const id = buildAssetIdentity({ kind: 'dataset', fingerprint: '  ', archive_path: '/a' })
    expect(id.idType).toBe('archive_path')
  })

  it('handles object source_uri (e.g. dataset with repo/split dict)', () => {
    const uri = { repo: 'my/repo', split: 'train' }
    const id = buildAssetIdentity({ kind: 'dataset', source_uri: uri, name: 'ds1' })
    expect(id.idType).toBe('source_uri')
    expect(id.idValue).toBe(JSON.stringify(uri))
  })
})

// ── assetIdentityToString ──

describe('assetIdentityToString', () => {
  it('produces correct "kind:idType:idValue" format', () => {
    const id: AssetIdentity = { kind: 'code', idType: 'fingerprint', idValue: 'abc' }
    expect(assetIdentityToString(id)).toBe('code:fingerprint:abc')
  })
})

// ── encodeAssetIdentity / decodeAssetIdentity round-trip ──

describe('encodeAssetIdentity / decodeAssetIdentity', () => {
  it('round-trips a basic identity', () => {
    const id: AssetIdentity = { kind: 'dataset', idType: 'fingerprint', idValue: 'abc123' }
    const encoded = encodeAssetIdentity(id)
    const decoded = decodeAssetIdentity(encoded)
    expect(decoded).toEqual(id)
  })

  it('round-trips identity with special characters (Chinese, /, =, +)', () => {
    const id: AssetIdentity = { kind: 'dataset', idType: 'name', idValue: '数据集/a+b=c' }
    const encoded = encodeAssetIdentity(id)
    const decoded = decodeAssetIdentity(encoded)
    expect(decoded).toEqual(id)
  })

  it('encoded string does not contain +, /, =', () => {
    const id: AssetIdentity = { kind: 'code', idType: 'fingerprint', idValue: 'test+/=value' }
    const encoded = encodeAssetIdentity(id)
    expect(encoded).not.toMatch(/[+/=]/)
  })

  it('returns null for non-base64 string', () => {
    expect(decodeAssetIdentity('!!!invalid!!!')).toBeNull()
  })

  it('returns null for valid base64 but invalid JSON', () => {
    const encoded = btoa('not-json').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
    expect(decodeAssetIdentity(encoded)).toBeNull()
  })

  it('returns null for JSON missing required fields', () => {
    const encoded = btoa(JSON.stringify({ kind: 'code' }))
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
    expect(decodeAssetIdentity(encoded)).toBeNull()
  })
})
