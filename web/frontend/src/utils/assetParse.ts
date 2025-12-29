import { AssetIdentity, buildAssetIdentity } from './assetIdentity'

type AssetKind = AssetIdentity['kind']

export type ParsedAsset = {
  kind: AssetKind
  name: string
  saved: boolean
  archive_path?: string
  source_uri?: string
  fingerprint?: string
  fingerprint_kind?: string
  description?: string
  context?: string
  source_type?: string
  meta?: any
  identity: AssetIdentity
}

function stableStringify(v: any): string {
  if (v === null || v === undefined) return ''
  if (typeof v !== 'object') return String(v)
  if (Array.isArray(v)) return `[${v.map(stableStringify).join(',')}]`
  const keys = Object.keys(v).sort()
  const parts = keys.map((k) => `${JSON.stringify(k)}:${stableStringify(v[k])}`)
  return `{${parts.join(',')}}`
}

function pickFingerprint(fp: any): string | undefined {
  if (!fp) return undefined
  if (typeof fp === 'string') return fp
  if (typeof fp === 'number') return String(fp)
  if (typeof fp === 'object') return stableStringify(fp)
  return undefined
}

export function parseRunAssetsPayload(payload: any): ParsedAsset[] {
  const a = payload?.assets
  if (!a || typeof a !== 'object') return []

  const out: ParsedAsset[] = []

  const codeSnap = a?.code?.snapshot
  if (codeSnap && typeof codeSnap === 'object') {
    const fingerprint = pickFingerprint(codeSnap.fingerprint)
    const identity = buildAssetIdentity({
      kind: 'code',
      fingerprint,
      archive_path: codeSnap.archive_path,
      source_uri: codeSnap.workspace_root,
      name: 'code_snapshot',
    })
    out.push({
      kind: 'code',
      name: 'code_snapshot',
      saved: Boolean(codeSnap.saved),
      archive_path: codeSnap.archive_path,
      source_uri: codeSnap.workspace_root,
      fingerprint,
      fingerprint_kind: codeSnap.fingerprint_kind,
      meta: codeSnap,
      identity,
    })
  }

  const cfg = a?.config
  if (cfg && typeof cfg === 'object' && Object.keys(cfg).length > 0) {
    const identity = buildAssetIdentity({ kind: 'config', name: 'config' })
    out.push({
      kind: 'config',
      name: 'config',
      saved: false,
      identity,
      meta: cfg,
    })
  }

  const datasets = Array.isArray(a?.datasets) ? a.datasets : []
  datasets.forEach((d: any, i: number) => {
    const name = String(d?.name ?? `dataset_${i}`)
    const fingerprint = pickFingerprint(d?.fingerprint)
    const description = d?.description != null ? String(d.description) : undefined
    const context = d?.context != null ? String(d.context) : undefined
    const identity = buildAssetIdentity({
      kind: 'dataset',
      fingerprint,
      archive_path: d?.archive_path,
      source_uri: d?.uri,
      name,
    })
    out.push({
      kind: 'dataset',
      name,
      saved: Boolean(d?.saved),
      archive_path: d?.archive_path,
      source_uri: d?.uri,
      fingerprint,
      fingerprint_kind: d?.fingerprint_kind,
      description,
      context,
      meta: d,
      identity,
    })
  })

  const pretrained = Array.isArray(a?.pretrained) ? a.pretrained : []
  pretrained.forEach((p: any, i: number) => {
    const name = String(p?.name ?? `pretrained_${i}`)
    const fingerprint = pickFingerprint(p?.fingerprint)
    const description = p?.description != null ? String(p.description) : undefined
    const source_type = p?.source_type != null ? String(p.source_type) : undefined
    const identity = buildAssetIdentity({
      kind: 'pretrained',
      fingerprint,
      archive_path: p?.archive_path,
      source_uri: p?.path_or_uri != null ? String(p.path_or_uri) : undefined,
      name,
    })
    out.push({
      kind: 'pretrained',
      name,
      saved: Boolean(p?.saved),
      archive_path: p?.archive_path,
      source_uri: p?.path_or_uri != null ? String(p.path_or_uri) : undefined,
      fingerprint,
      fingerprint_kind: p?.fingerprint_kind,
      description,
      source_type,
      meta: p,
      identity,
    })
  })

  const outputs = Array.isArray(a?.outputs) ? a.outputs : []
  outputs.forEach((e: any, i: number) => {
    const name = String(e?.name ?? e?.key ?? `output_${i}`)
    const fingerprint = pickFingerprint(e?.fingerprint)
    const identity = buildAssetIdentity({
      kind: 'output',
      fingerprint,
      archive_path: e?.archive_path,
      source_uri: e?.path,
      name,
    })
    out.push({
      kind: 'output',
      name,
      saved: true,
      archive_path: e?.archive_path,
      source_uri: e?.path,
      fingerprint,
      fingerprint_kind: e?.fingerprint_kind,
      meta: e,
      identity,
    })
  })

  return out
}
