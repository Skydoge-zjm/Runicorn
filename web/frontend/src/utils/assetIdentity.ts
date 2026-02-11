export type AssetIdentity = {
  kind: 'code' | 'config' | 'dataset' | 'pretrained' | 'output' | 'custom'
  idType: 'fingerprint' | 'archive_path' | 'source_uri' | 'name'
  idValue: string
}

function base64UrlEncode(input: string): string {
  const bytes = new TextEncoder().encode(input)
  let binary = ''
  bytes.forEach((b) => {
    binary += String.fromCharCode(b)
  })
  const base64 = btoa(binary)
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function base64UrlDecode(input: string): string {
  const b64 = input.replace(/-/g, '+').replace(/_/g, '/')
  const pad = b64.length % 4 === 0 ? '' : '='.repeat(4 - (b64.length % 4))
  const binary = atob(b64 + pad)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return new TextDecoder().decode(bytes)
}

export function assetIdentityToString(id: AssetIdentity): string {
  return `${id.kind}:${id.idType}:${id.idValue}`
}

export function encodeAssetIdentity(id: AssetIdentity): string {
  return base64UrlEncode(JSON.stringify(id))
}

export function decodeAssetIdentity(encoded: string): AssetIdentity | null {
  try {
    const raw = base64UrlDecode(encoded)
    const obj = JSON.parse(raw)
    if (!obj || typeof obj !== 'object') return null
    if (!obj.kind || !obj.idType || !obj.idValue) return null
    return obj as AssetIdentity
  } catch {
    return null
  }
}

export function buildAssetIdentity(input: {
  kind: AssetIdentity['kind']
  fingerprint?: string | null
  archive_path?: string | null
  source_uri?: string | null
  name?: string | null
}): AssetIdentity {
  const kind = input.kind
  const fp = (input.fingerprint ?? '').trim()
  if (fp) return { kind, idType: 'fingerprint', idValue: fp }

  const ap = (input.archive_path ?? '').trim()
  if (ap) return { kind, idType: 'archive_path', idValue: ap }

  const su = (input.source_uri ?? '').trim()
  if (su) return { kind, idType: 'source_uri', idValue: su }

  const n = (input.name ?? '').trim()
  return { kind, idType: 'name', idValue: n || '-' }
}
