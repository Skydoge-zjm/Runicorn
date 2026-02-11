/**
 * Hook for managing saved SSH connections
 */

import { useMemo, useState, useEffect, useCallback } from 'react'
import type {
  AuthMethod,
  SavedConnection,
  SavedConnectionProfile,
  SavedEntry,
  SavedServer,
  SSHConnectionConfig
} from '../types/remote'

const API_BASE = '/api/remote/connections/saved'

function generateId(): string {
  return `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

function normalizeIdPart(value: string): string {
  return value.replace(/[^a-zA-Z0-9]/g, '_')
}

function buildServerId(payload: { host: string; port: number; username: string }): string {
  return `srv_${normalizeIdPart(payload.username)}_${normalizeIdPart(payload.host)}_${payload.port}`
}

function isSavedEntry(value: unknown): value is SavedEntry {
  return (
    !!value &&
    typeof value === 'object' &&
    'kind' in value &&
    (((value as { kind?: unknown }).kind === 'server') || ((value as { kind?: unknown }).kind === 'connection'))
  )
}

function migrateLegacyConnections(items: SavedConnection[]): SavedEntry[] {
  const serverMap = new Map<string, SavedServer>()
  const profiles: SavedConnectionProfile[] = []

  for (const conn of items) {
    const authMethod: AuthMethod = conn.authMethod || 'password'
    const serverId = buildServerId({ host: conn.host, port: conn.port, username: conn.username })

    const existing = serverMap.get(serverId)
    if (!existing) {
      serverMap.set(serverId, {
        kind: 'server',
        id: serverId,
        name: `${conn.username}@${conn.host}:${conn.port}`,
        host: conn.host,
        port: conn.port,
        username: conn.username,
        authMethod,
        password: conn.password || undefined,
        privateKeyPath: conn.privateKeyPath,
        passphrase: (conn as unknown as { passphrase?: string }).passphrase,
        createdAt: conn.createdAt || Date.now()
      })
    } else {
      const merged: SavedServer = {
        ...existing,
        authMethod:
          (existing.password ?? conn.password) ? 'password' : (existing.privateKeyPath ?? conn.privateKeyPath) ? 'key' : existing.authMethod,
        password: existing.password ?? conn.password ?? undefined,
        privateKeyPath: existing.privateKeyPath ?? conn.privateKeyPath,
        passphrase: existing.passphrase ?? (conn as unknown as { passphrase?: string }).passphrase,
        createdAt: Math.min(existing.createdAt || Date.now(), conn.createdAt || Date.now())
      }
      serverMap.set(serverId, merged)
    }

    profiles.push({
      kind: 'connection',
      id: conn.id,
      serverId,
      name: conn.name,
      condaEnv: conn.condaEnv,
      remoteRoot: conn.remoteRoot,
      localPort: conn.localPort,
      remotePort: conn.remotePort,
      createdAt: conn.createdAt || Date.now()
    })
  }

  return [...serverMap.values(), ...profiles]
}

function normalizeSavedEntries(list: SavedEntry[]): { entries: SavedEntry[]; changed: boolean } {
  let changed = false

  const orderedServers: SavedServer[] = []
  const serverByCanonicalId = new Map<string, SavedServer>()
  const idRemap = new Map<string, string>()

  for (const entry of list) {
    if (entry.kind !== 'server') continue

    const canonicalId = buildServerId({ host: entry.host, port: entry.port, username: entry.username })
    idRemap.set(entry.id, canonicalId)
    if (entry.id !== canonicalId) changed = true

    const existing = serverByCanonicalId.get(canonicalId)
    if (!existing) {
      const normalized: SavedServer = { ...entry, kind: 'server', id: canonicalId }
      serverByCanonicalId.set(canonicalId, normalized)
      orderedServers.push(normalized)
      continue
    }

    const merged: SavedServer = {
      ...existing,
      name: existing.name || entry.name,
      password: existing.password ?? entry.password,
      privateKeyPath: existing.privateKeyPath ?? entry.privateKeyPath,
      passphrase: existing.passphrase ?? entry.passphrase,
      createdAt: Math.min(existing.createdAt || Date.now(), entry.createdAt || Date.now()),
      authMethod:
        (existing.password ?? entry.password)
          ? 'password'
          : (existing.privateKeyPath ?? entry.privateKeyPath)
            ? 'key'
            : existing.authMethod || entry.authMethod
    }

    serverByCanonicalId.set(canonicalId, merged)
    const idx = orderedServers.findIndex(s => s.id === canonicalId)
    if (idx >= 0) {
      orderedServers[idx] = merged
    }
    changed = true
  }

  const normalizedProfiles: SavedConnectionProfile[] = []
  for (const entry of list) {
    if (entry.kind !== 'connection') continue
    const newServerId = idRemap.get(entry.serverId) ?? entry.serverId
    if (newServerId !== entry.serverId) changed = true
    normalizedProfiles.push({ ...entry, kind: 'connection', serverId: newServerId })
  }

  return { entries: [...orderedServers, ...normalizedProfiles], changed }
}

// Helper to clean undefined values (convert to null for JSON serialization)
function cleanForJson<T extends Record<string, any>>(obj: T): T {
  const cleaned = { ...obj }
  Object.keys(cleaned).forEach(key => {
    if (cleaned[key] === undefined) {
      delete cleaned[key]  // Remove undefined fields
    }
  })
  return cleaned
}

export function useSavedConnections() {
  const [entries, setEntries] = useState<SavedEntry[]>([])
  const [loading, setLoading] = useState(false)

  // Load from backend API on mount
  useEffect(() => {
    const loadConnections = async () => {
      try {
        setLoading(true)
        const response = await fetch(API_BASE)
        if (response.ok) {
          const data = await response.json()
          const raw = (data as { connections?: unknown }).connections
          const list = Array.isArray(raw) ? raw : []
          if (list.length === 0) {
            setEntries([])
            return
          }

          if (list.every(isSavedEntry)) {
            const normalized = normalizeSavedEntries(list as SavedEntry[])
            setEntries(normalized.entries)
            if (normalized.changed) {
              const cleaned = normalized.entries.map(e => cleanForJson(e as unknown as Record<string, any>))
              await fetch(API_BASE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cleaned)
              }).catch(() => {})
            }
            return
          }

          const migrated = migrateLegacyConnections(list as SavedConnection[])
          setEntries(migrated)
          const cleaned = migrated.map(e => cleanForJson(e as unknown as Record<string, any>))
          await fetch(API_BASE, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cleaned)
          }).catch(() => {})
        }
      } catch (error) {
        console.error('Failed to load saved connections:', error)
      } finally {
        setLoading(false)
      }
    }
    loadConnections()
  }, [])

  const servers = useMemo(() => {
    return entries.filter((e): e is SavedServer => e.kind === 'server')
  }, [entries])

  const profiles = useMemo(() => {
    return entries.filter((e): e is SavedConnectionProfile => e.kind === 'connection')
  }, [entries])

  const getProfilesForServer = useCallback(
    (serverId: string) => profiles.filter(p => p.serverId === serverId),
    [profiles]
  )

  const persist = useCallback(
    async (nextEntries: SavedEntry[]) => {
      const cleaned = nextEntries.map(e => cleanForJson(e as unknown as Record<string, any>))
      const response = await fetch(API_BASE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cleaned)
      })
      if (!response.ok) {
        throw new Error('Failed to save connections')
      }
      setEntries(nextEntries)
    },
    []
  )

  const addServer = useCallback(async (payload: Omit<SavedServer, 'kind' | 'id' | 'createdAt' | 'name'> & { name?: string }) => {
    const serverId = buildServerId({ host: payload.host, port: payload.port, username: payload.username })

    const existing = entries.find((e): e is SavedServer => e.kind === 'server' && e.id === serverId)

    const next: SavedServer = {
      kind: 'server',
      id: serverId,
      name: payload.name || existing?.name || `${payload.username}@${payload.host}:${payload.port}`,
      host: payload.host,
      port: payload.port,
      username: payload.username,
      authMethod: payload.authMethod,
      password: payload.password ?? existing?.password,
      privateKeyPath: payload.privateKeyPath ?? existing?.privateKeyPath,
      passphrase: payload.passphrase ?? existing?.passphrase,
      createdAt: existing?.createdAt || Date.now()
    }

    const withoutOld = entries.filter(e => !(e.kind === 'server' && e.id === serverId))
    await persist([...withoutOld, next])
    return serverId
  }, [entries, persist])

  const updateServer = useCallback(async (id: string, updates: Partial<SavedServer>) => {
    const next = entries.map(e => {
      if (e.kind !== 'server' || e.id !== id) return e
      return { ...e, ...updates, kind: 'server', id } as SavedServer
    })
    await persist(next)
  }, [entries, persist])

  const deleteServer = useCallback(async (id: string) => {
    const next = entries.filter(e => {
      if (e.kind === 'server' && e.id === id) return false
      if (e.kind === 'connection' && e.serverId === id) return false
      return true
    })
    await persist(next)
  }, [entries, persist])

  const addProfile = useCallback(async (serverId: string, payload: Omit<SavedConnectionProfile, 'kind' | 'id' | 'serverId' | 'createdAt'> & { name?: string }) => {
    const next: SavedConnectionProfile = {
      kind: 'connection',
      id: generateId(),
      serverId,
      name: payload.name || 'New Connection',
      condaEnv: payload.condaEnv,
      remoteRoot: payload.remoteRoot,
      localPort: payload.localPort,
      remotePort: payload.remotePort,
      createdAt: Date.now()
    }
    await persist([...entries, next])
    return next.id
  }, [entries, persist])

  const updateProfile = useCallback(async (id: string, updates: Partial<SavedConnectionProfile>) => {
    const next = entries.map(e => {
      if (e.kind !== 'connection' || e.id !== id) return e
      return { ...e, ...updates, kind: 'connection', id } as SavedConnectionProfile
    })
    await persist(next)
  }, [entries, persist])

  const deleteProfile = useCallback(async (id: string) => {
    const next = entries.filter(e => !(e.kind === 'connection' && e.id === id))
    await persist(next)
  }, [entries, persist])

  const getServer = useCallback((id: string) => {
    return servers.find(s => s.id === id)
  }, [servers])

  const getProfile = useCallback((id: string) => {
    return profiles.find(p => p.id === id)
  }, [profiles])

  const saveConnection = useCallback(async (config: SSHConnectionConfig, condaEnv?: string) => {
    const serverId = await addServer({
      name: config.saveName,
      host: config.host,
      port: config.port,
      username: config.username,
      authMethod: config.authMethod,
      password: config.password,
      privateKeyPath: config.privateKeyPath
    })

    const profileId = await addProfile(serverId, {
      name: config.saveName || `${config.username}@${config.host}`,
      condaEnv: condaEnv ?? config.condaEnv,
      remoteRoot: config.remoteRoot,
      localPort: config.localPort,
      remotePort: config.remotePort
    })

    return profileId
  }, [addProfile, addServer])

  return {
    entries,
    servers,
    profiles,
    getProfilesForServer,
    loading,
    saveConnection,
    addServer,
    updateServer,
    deleteServer,
    addProfile,
    updateProfile,
    deleteProfile,
    getServer,
    getProfile
  }
}
