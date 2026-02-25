import { describe, it, expect } from 'vitest'
import { parseRunAssetsPayload } from './assetParse'

describe('parseRunAssetsPayload', () => {
  it('returns [] for null', () => {
    expect(parseRunAssetsPayload(null)).toEqual([])
  })

  it('returns [] for undefined', () => {
    expect(parseRunAssetsPayload(undefined)).toEqual([])
  })

  it('returns [] for empty object', () => {
    expect(parseRunAssetsPayload({})).toEqual([])
  })

  it('returns [] when assets key is missing', () => {
    expect(parseRunAssetsPayload({ foo: 1 })).toEqual([])
  })

  it('parses code snapshot', () => {
    const payload = {
      assets: {
        code: {
          snapshot: {
            saved: true,
            archive_path: '/archive/snap.zip',
            workspace_root: '/home/user/proj',
            fingerprint: 'fp123',
            fingerprint_kind: 'sha256',
          },
        },
      },
    }
    const result = parseRunAssetsPayload(payload)
    expect(result).toHaveLength(1)
    expect(result[0].kind).toBe('code')
    expect(result[0].name).toBe('code_snapshot')
    expect(result[0].saved).toBe(true)
    expect(result[0].fingerprint).toBe('fp123')
    expect(result[0].identity.idType).toBe('fingerprint')
  })

  it('parses config', () => {
    const payload = { assets: { config: { lr: 0.01, batch_size: 32 } } }
    const result = parseRunAssetsPayload(payload)
    expect(result).toHaveLength(1)
    expect(result[0].kind).toBe('config')
    expect(result[0].name).toBe('config')
    expect(result[0].saved).toBe(false)
  })

  it('skips empty config object', () => {
    const payload = { assets: { config: {} } }
    expect(parseRunAssetsPayload(payload)).toEqual([])
  })

  it('parses multiple datasets', () => {
    const payload = {
      assets: {
        datasets: [
          { name: 'train', fingerprint: 'fp1', uri: 's3://bucket/train' },
          { name: 'val', fingerprint: 'fp2' },
        ],
      },
    }
    const result = parseRunAssetsPayload(payload)
    expect(result).toHaveLength(2)
    expect(result[0].kind).toBe('dataset')
    expect(result[0].name).toBe('train')
    expect(result[0].source_uri).toBe('s3://bucket/train')
    expect(result[1].name).toBe('val')
  })

  it('parses pretrained with source_type and description', () => {
    const payload = {
      assets: {
        pretrained: [
          { name: 'bert', source_type: 'huggingface', description: 'BERT base', path_or_uri: 'hf://bert' },
        ],
      },
    }
    const result = parseRunAssetsPayload(payload)
    expect(result).toHaveLength(1)
    expect(result[0].kind).toBe('pretrained')
    expect(result[0].source_type).toBe('huggingface')
    expect(result[0].description).toBe('BERT base')
    expect(result[0].source_uri).toBe('hf://bert')
  })

  it('parses outputs with saved always true', () => {
    const payload = {
      assets: {
        outputs: [
          { name: 'model.pt', archive_path: '/archive/model.pt' },
        ],
      },
    }
    const result = parseRunAssetsPayload(payload)
    expect(result).toHaveLength(1)
    expect(result[0].kind).toBe('output')
    expect(result[0].saved).toBe(true)
  })

  it('produces correct order: code → config → datasets → pretrained → outputs', () => {
    const payload = {
      assets: {
        outputs: [{ name: 'out' }],
        code: { snapshot: { saved: true, archive_path: '/a' } },
        config: { lr: 1 },
        datasets: [{ name: 'ds' }],
        pretrained: [{ name: 'pt' }],
      },
    }
    const result = parseRunAssetsPayload(payload)
    expect(result.map((a) => a.kind)).toEqual(['code', 'config', 'dataset', 'pretrained', 'output'])
  })

  it('handles fingerprint as object via stableStringify', () => {
    const payload = {
      assets: {
        datasets: [{ name: 'ds', fingerprint: { b: 1, a: 2 } }],
      },
    }
    const result = parseRunAssetsPayload(payload)
    expect(result[0].fingerprint).toBe('{"a":2,"b":1}')
  })

  it('handles fingerprint as number', () => {
    const payload = {
      assets: {
        datasets: [{ name: 'ds', fingerprint: 42 }],
      },
    }
    const result = parseRunAssetsPayload(payload)
    expect(result[0].fingerprint).toBe('42')
  })

  it('uses default naming when name is missing', () => {
    const payload = {
      assets: {
        datasets: [{ fingerprint: 'fp' }],
      },
    }
    const result = parseRunAssetsPayload(payload)
    expect(result[0].name).toBe('dataset_0')
  })
})
