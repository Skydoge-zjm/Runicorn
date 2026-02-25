import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../__mocks__/server'
import {
  connectRemote,
  listRemoteSessions,
  startRemoteViewer,
  listSSHSessions,
} from '../remote'
import { ApiError } from '../../types/remote'

const baseConfig = {
  host: 'test-host',
  port: 22,
  username: 'user',
  authMethod: 'password' as const,
  password: 'pass',
}

describe('connectRemote', () => {
  it('returns SSHSession on success', async () => {
    const session = await connectRemote(baseConfig)
    expect(session.host).toBe('test')
    expect(session.status).toBe('connected')
  })

  it('throws ApiError on failure', async () => {
    server.use(
      http.post('/api/remote/connect', () =>
        HttpResponse.json({ detail: 'Auth failed' }, { status: 401 }),
      ),
    )
    await expect(connectRemote(baseConfig)).rejects.toThrow(ApiError)
  })
})

describe('listSSHSessions', () => {
  it('returns sessions array', async () => {
    const sessions = await listSSHSessions()
    expect(Array.isArray(sessions)).toBe(true)
  })
})

describe('startRemoteViewer', () => {
  it('throws local Error when remoteRoot is missing', async () => {
    await expect(startRemoteViewer(baseConfig)).rejects.toThrow(
      'Remote storage root is required',
    )
  })

  it('returns RemoteSession on success', async () => {
    const config = { ...baseConfig, remoteRoot: '/home/user/data' }
    const session = await startRemoteViewer(config)
    expect(session.sessionId).toBe('s1')
  })
})

describe('listRemoteSessions', () => {
  it('returns sessions array', async () => {
    const sessions = await listRemoteSessions()
    expect(Array.isArray(sessions)).toBe(true)
  })
})
