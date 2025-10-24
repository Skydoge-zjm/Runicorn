/**
 * Hook for managing saved SSH connections
 */

import { useState, useEffect, useCallback } from 'react'
import { SavedConnection, SSHConnectionConfig } from '../types/remote'

const API_BASE = '/api/remote/connections/saved'

function generateId(): string {
  return `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
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
  const [connections, setConnections] = useState<SavedConnection[]>([])
  const [loading, setLoading] = useState(false)

  // Load from backend API on mount
  useEffect(() => {
    const loadConnections = async () => {
      try {
        setLoading(true)
        const response = await fetch(API_BASE)
        if (response.ok) {
          const data = await response.json()
          setConnections(data.connections || [])
        }
      } catch (error) {
        console.error('Failed to load saved connections:', error)
      } finally {
        setLoading(false)
      }
    }
    loadConnections()
  }, [])

  // Save connection
  const saveConnection = useCallback(async (config: SSHConnectionConfig, condaEnv?: string) => {
    const newConnection: SavedConnection = {
      id: generateId(),
      name: config.saveName || `${config.username}@${config.host}`,
      host: config.host,
      port: config.port,
      username: config.username,
      authMethod: config.authMethod,
      password: config.password || undefined, // Save password if provided (user chose to save it)
      privateKeyPath: config.privateKeyPath,
      condaEnv: condaEnv,
      remoteRoot: config.remoteRoot,
      localPort: config.localPort,
      remotePort: config.remotePort,
      createdAt: Date.now()
    }
    
    console.log('Creating new connection:', {
      name: newConnection.name,
      hasPassword: !!newConnection.password,
      hasRemoteRoot: !!newConnection.remoteRoot,
      condaEnv: newConnection.condaEnv
    })

    const updated = [...connections, cleanForJson(newConnection)]
    
    try {
      const response = await fetch(API_BASE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated)
      })
      
      if (!response.ok) {
        throw new Error('Failed to save connections')
      }
      
      setConnections(updated)
    } catch (error) {
      console.error('Failed to save connection:', error)
      throw error
    }

    return newConnection.id
  }, [connections])

  // Update connection
  const updateConnection = useCallback(async (id: string, updates: Partial<SavedConnection>) => {
    const updated = connections.map(conn =>
      conn.id === id ? cleanForJson({ ...conn, ...updates }) : conn
    )
    
    console.log('Updating connection:', { id, updates })
    
    try {
      const response = await fetch(API_BASE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated)
      })
      
      if (!response.ok) {
        throw new Error('Failed to update connection')
      }
      
      setConnections(updated)
    } catch (error) {
      console.error('Failed to update connection:', error)
      throw error
    }
  }, [connections])

  // Delete connection
  const deleteConnection = useCallback(async (id: string) => {
    const updated = connections.filter(conn => conn.id !== id)
    
    try {
      const response = await fetch(API_BASE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated)
      })
      
      if (!response.ok) {
        throw new Error('Failed to delete connection')
      }
      
      setConnections(updated)
    } catch (error) {
      console.error('Failed to delete connection:', error)
      throw error
    }
  }, [connections])

  // Get connection by ID
  const getConnection = useCallback((id: string) => {
    return connections.find(conn => conn.id === id)
  }, [connections])

  return {
    connections,
    loading,
    saveConnection,
    updateConnection,
    deleteConnection,
    getConnection
  }
}
