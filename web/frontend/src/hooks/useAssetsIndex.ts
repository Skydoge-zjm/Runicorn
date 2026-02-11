import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { message } from 'antd'
import { getRunAssets, listRuns } from '../api'
import { ParsedAsset, parseRunAssetsPayload } from '../utils/assetParse'
import { AssetIdentity, assetIdentityToString, encodeAssetIdentity } from '../utils/assetIdentity'

export type AssetsIndexRun = {
  run_id: string
  path: string
  alias: string | null
  created_time?: number
  status?: string
  assets_count?: number
}

export type AssetsIndexExperimentRow = {
  key: string
  path: string
  runs_count: number
  assets_total: number
  archived_total: number
  by_kind: Record<string, number>
  run_ids: string[]
}

export type AssetsIndexRepoRow = {
  key: string
  encoded: string
  identity: AssetIdentity
  kind: AssetIdentity['kind']
  name: string
  saved: boolean
  fingerprint?: string
  archive_path?: string
  source_uri?: string
  description?: string
  context?: string
  source_type?: string
  paths: string[]
  runs_count: number
  last_used_time?: number
  run_ids: string[]
}

export type AssetsIndex = {
  version: number
  generated_at: number
  runs: AssetsIndexRun[]
  run_assets: Record<string, ParsedAsset[]>
  experiments: AssetsIndexExperimentRow[]
  repo: AssetsIndexRepoRow[]
}

const STORAGE_KEY = 'assets_index_v3'

function nowSec(): number {
  return Math.floor(Date.now() / 1000)
}

function safeParseJson(s: string | null): any {
  if (!s) return null
  try {
    return JSON.parse(s)
  } catch {
    return null
  }
}

async function mapLimit<T, R>(items: T[], limit: number, fn: (item: T, idx: number) => Promise<R>): Promise<R[]> {
  const out: R[] = new Array(items.length)
  let i = 0

  const workers = new Array(Math.max(1, limit)).fill(0).map(async () => {
    while (true) {
      const cur = i
      i += 1
      if (cur >= items.length) return
      out[cur] = await fn(items[cur], cur)
    }
  })

  await Promise.all(workers)
  return out
}

function normalizeRun(r: any): AssetsIndexRun {
  return {
    run_id: String(r?.id || r?.run_id || ''),
    path: String(r?.path || 'default'),
    alias: r?.alias || null,
    created_time: typeof r?.created_time === 'number' ? r.created_time : undefined,
    status: r?.status != null ? String(r.status) : undefined,
    assets_count: typeof r?.assets_count === 'number' ? r.assets_count : undefined,
  }
}

function buildIndexFromRuns(runs: AssetsIndexRun[], runAssets: Record<string, ParsedAsset[]>): Pick<AssetsIndex, 'experiments' | 'repo'> {
  const expMap = new Map<string, AssetsIndexExperimentRow>()

  const repoMap = new Map<
    string,
    {
      identity: AssetIdentity
      kind: AssetIdentity['kind']
      name: string
      saved: boolean
      fingerprint?: string
      archive_path?: string
      source_uri?: string
      description?: string
      context?: string
      source_type?: string
      paths: Set<string>
      run_ids: Set<string>
      last_used_time?: number
    }
  >()

  const runTime = new Map<string, number>()
  runs.forEach((r) => {
    if (r.created_time) runTime.set(r.run_id, r.created_time)
  })

  runs.forEach((r) => {
    const assets = runAssets[r.run_id] || []
    if (assets.length === 0) return

    const expKey = r.path
    const row = expMap.get(expKey) || {
      key: expKey,
      path: r.path,
      runs_count: 0,
      assets_total: 0,
      archived_total: 0,
      by_kind: { code: 0, config: 0, dataset: 0, pretrained: 0, output: 0 },
      run_ids: [],
    }

    row.runs_count += 1
    row.assets_total += assets.length
    row.archived_total += assets.filter((a) => Boolean(a.saved)).length
    assets.forEach((a) => {
      row.by_kind[a.kind] = (row.by_kind[a.kind] || 0) + 1

      const k = assetIdentityToString(a.identity)
      const existing = repoMap.get(k) || {
        identity: a.identity,
        kind: a.kind,
        name: a.name,
        saved: Boolean(a.saved),
        fingerprint: a.fingerprint,
        archive_path: a.archive_path,
        source_uri: a.source_uri,
        description: a.description,
        context: a.context,
        source_type: a.source_type,
        paths: new Set<string>(),
        run_ids: new Set<string>(),
        last_used_time: undefined as number | undefined,
      }

      existing.saved = existing.saved || Boolean(a.saved)
      if (!existing.fingerprint && a.fingerprint) existing.fingerprint = a.fingerprint
      if (!existing.archive_path && a.archive_path) existing.archive_path = a.archive_path
      if (!existing.source_uri && a.source_uri) existing.source_uri = a.source_uri
      if (!existing.description && a.description) existing.description = a.description
      if (!existing.context && a.context) existing.context = a.context
      if (!existing.source_type && a.source_type) existing.source_type = a.source_type

      existing.paths.add(r.path)
      existing.run_ids.add(r.run_id)
      const ts = runTime.get(r.run_id)
      if (typeof ts === 'number') {
        existing.last_used_time = Math.max(existing.last_used_time || 0, ts)
      }

      repoMap.set(k, existing)
    })

    row.run_ids.push(r.run_id)
    expMap.set(expKey, row)
  })

  const experiments = Array.from(expMap.values()).sort((a, b) => {
    return a.path.localeCompare(b.path)
  })

  const repo = Array.from(repoMap.entries())
    .map(([key, v]) => {
      const encoded = encodeAssetIdentity(v.identity)
      return {
        key,
        encoded,
        identity: v.identity,
        kind: v.kind,
        name: v.name,
        saved: Boolean(v.saved),
        fingerprint: v.fingerprint,
        archive_path: v.archive_path,
        source_uri: v.source_uri,
        description: v.description,
        context: v.context,
        source_type: v.source_type,
        paths: Array.from(v.paths.values()).sort(),
        runs_count: v.run_ids.size,
        last_used_time: v.last_used_time,
        run_ids: Array.from(v.run_ids.values()),
      } satisfies AssetsIndexRepoRow
    })
    .sort((a, b) => {
      const ta = a.last_used_time || 0
      const tb = b.last_used_time || 0
      if (ta !== tb) return tb - ta
      return a.name.localeCompare(b.name)
    })

  return { experiments, repo }
}

export function loadAssetsIndexFromCache(): AssetsIndex | null {
  const obj = safeParseJson(localStorage.getItem(STORAGE_KEY))
  if (!obj || typeof obj !== 'object') return null
  if (obj.version !== 3) return null
  if (!obj.generated_at || !obj.runs || !obj.run_assets) return null
  return obj as AssetsIndex
}

export function useAssetsIndex() {
  const [index, setIndex] = useState<AssetsIndex | null>(() => loadAssetsIndexFromCache())
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState<{ total: number; done: number }>({ total: 0, done: 0 })
  const abortRef = useRef<{ aborted: boolean }>({ aborted: false })
  const didAutoRefreshRef = useRef(false)

  const refresh = useCallback(async () => {
    abortRef.current.aborted = false
    setLoading(true)

    try {
      const rawRuns = await listRuns()
      const runs = (Array.isArray(rawRuns) ? rawRuns : []).map(normalizeRun)
      const candidatesByCount = runs.filter((r) => (r.assets_count || 0) > 0)
      const candidates = candidatesByCount.length > 0 ? candidatesByCount : runs

      setProgress({ total: candidates.length, done: 0 })

      const runAssets: Record<string, ParsedAsset[]> = {}

      let done = 0
      let failed = 0

      await mapLimit(candidates, 6, async (r, idx) => {
        if (abortRef.current.aborted) return

        try {
          const payload = await getRunAssets(r.run_id)
          runAssets[r.run_id] = parseRunAssetsPayload(payload)
        } catch {
          failed += 1
          runAssets[r.run_id] = []
        } finally {
          done += 1
          setProgress((p: { total: number; done: number }) => ({ total: p.total, done: Math.min(p.total, done) }))
        }
      })

      const { experiments, repo } = buildIndexFromRuns(runs, runAssets)
      const next: AssetsIndex = {
        version: 3,
        generated_at: nowSec(),
        runs,
        run_assets: runAssets,
        experiments,
        repo,
      }

      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      setIndex(next)
      if (failed > 0) {
        message.warning(`Assets index: ${failed} runs failed to fetch assets`)
      }
    } catch (e: any) {
      message.error(String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  const cancel = useCallback(() => {
    abortRef.current.aborted = true
  }, [])

  const stats = useMemo(() => {
    const totalRuns = index?.runs?.length || 0
    const runsWithAssets = Object.keys(index?.run_assets || {}).length
    const totalAssets = index?.repo?.length || 0
    const archivedAssets = (index?.repo || []).filter((r: AssetsIndexRepoRow) => r.saved).length
    return { totalRuns, runsWithAssets, totalAssets, archivedAssets }
  }, [index])

  useEffect(() => {
    if (!didAutoRefreshRef.current) {
      const runsLen = index?.runs?.length || 0
      const repoLen = index?.repo?.length || 0
      const shouldAutoRefresh =
        (!index && !loading) ||
        (!loading && Boolean(index) && (runsLen === 0 || (runsLen > 0 && repoLen === 0)))

      if (shouldAutoRefresh) {
        didAutoRefreshRef.current = true
        refresh()
      }
    }
  }, [index, loading, refresh])

  useEffect(() => {
    return () => {
      abortRef.current.aborted = true
    }
  }, [])

  return { index, loading, progress, stats, refresh, cancel }
}
