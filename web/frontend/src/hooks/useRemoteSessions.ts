/**
 * Hook for managing Remote Viewer sessions
 */

import { useState, useEffect, useCallback } from 'react'
import { RemoteSession } from '../types/remote'
import { listRemoteSessions } from '../api/remote'

export function useRemoteSessions() {
  const [sessions, setSessions] = useState<RemoteSession[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSessions = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listRemoteSessions()
      setSessions(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch sessions')
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-refresh sessions every 5 seconds
  useEffect(() => {
    fetchSessions()
    const interval = setInterval(fetchSessions, 5000)
    return () => clearInterval(interval)
  }, [fetchSessions])

  return {
    sessions,
    loading,
    error,
    refetch: fetchSessions
  }
}
