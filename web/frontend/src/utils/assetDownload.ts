export function sanitizeFilename(name: string): string {
  return String(name || '')
    .replace(/[\\/]+/g, '_')
    .replace(/\s+/g, ' ')
    .trim()
}

export function suggestAssetDownloadFilename(asset: any): string {
  const kind = String(asset?.kind || '')

  if (kind === 'code') return 'code_snapshot.zip'
  if (kind === 'config') return 'config.json'

  const metaName = asset?.meta?.name ?? asset?.meta?.key
  let base = sanitizeFilename(String(metaName ?? asset?.name ?? 'asset'))
  if (!base) base = 'asset'

  const ap = String(asset?.archive_path || '')
  if (ap.toLowerCase().endsWith('.zip') && !base.toLowerCase().endsWith('.zip')) {
    base = `${base}.zip`
  }

  return base
}

export function isProbablyTextFilename(name: string): boolean {
  const n = String(name || '').toLowerCase()
  if (!n) return false

  const exts = [
    '.txt',
    '.log',
    '.md',
    '.json',
    '.yaml',
    '.yml',
    '.toml',
    '.ini',
    '.cfg',
    '.py',
    '.ts',
    '.tsx',
    '.js',
    '.jsx',
    '.css',
    '.html',
    '.sh',
    '.bat',
    '.ps1',
    '.csv',
  ]

  return exts.some((e) => n.endsWith(e))
}
