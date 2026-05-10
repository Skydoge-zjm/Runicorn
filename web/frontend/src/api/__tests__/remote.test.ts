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

  it('forwards savedServerId for server-side credential lookup', async () => {
    server.use(
      http.post('/api/remote/connect', async ({ request }) => {
        const body = await request.json() as any
        return HttpResponse.json({
          host: body.host,
          status: 'connected',
          saved_server_id: body.saved_server_id,
        })
      }),
    )

    const session = await connectRemote({ ...baseConfig, savedServerId: 'srv_1', password: undefined })
    expect((session as any).saved_server_id).toBe('srv_1')
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

// ── Additional remote.ts coverage ──

import {
  disconnectRemote,
  stopRemoteViewer,
  getSessionStatus,
  listRemoteStorageCandidates,
  testConnection,
  listKnownHosts,
  removeKnownHost,
  listCondaEnvs,
  getEnvConfigs,
  getRemoteConfig,
  acceptKnownHost,
  quickStartRemoteViewer,
  getLocalVersion,
} from '../remote'

describe('disconnectRemote', () => {
  it('succeeds on 200', async () => {
    await expect(disconnectRemote('test-host', 22, 'user')).resolves.toBeUndefined()
  })

  it('throws ApiError on failure', async () => {
    server.use(
      http.post('/api/remote/disconnect', () =>
        HttpResponse.json({ detail: 'Not connected' }, { status: 400 }),
      ),
    )
    await expect(disconnectRemote('h', 22, 'u')).rejects.toThrow(ApiError)
  })
})

describe('stopRemoteViewer', () => {
  it('succeeds on 200', async () => {
    await expect(stopRemoteViewer('s1')).resolves.toBeUndefined()
  })

  it('throws on failure', async () => {
    server.use(
      http.post('/api/remote/viewer/stop', () =>
        HttpResponse.json({ detail: 'Not found' }, { status: 404 }),
      ),
    )
    await expect(stopRemoteViewer('bad')).rejects.toThrow(ApiError)
  })
})

describe('getSessionStatus', () => {
  it('returns session info', async () => {
    server.use(
      http.get('/api/remote/viewer/status/:id', () =>
        HttpResponse.json({ sessionId: 's1', status: 'running' }),
      ),
    )
    const data = await getSessionStatus('s1')
    expect(data.status).toBe('running')
  })
})

describe('listRemoteStorageCandidates', () => {
  it('returns storage candidates', async () => {
    server.use(
      http.get('/api/remote/storage-candidates', () =>
        HttpResponse.json({
          candidates: [
            {
              path: '/home/user/runicorn_data',
              run_count: 3,
              has_archive: true,
              has_index: true,
            },
          ],
        }),
      ),
    )
    const entries = await listRemoteStorageCandidates('conn1', 'myenv')
    expect(entries).toHaveLength(1)
    expect(entries[0].path).toBe('/home/user/runicorn_data')
    expect(entries[0].runCount).toBe(3)
    expect(entries[0].hasArchive).toBe(true)
  })
})

describe('testConnection', () => {
  it('returns success when connect+disconnect succeed', async () => {
    const result = await testConnection(baseConfig)
    expect(result.success).toBe(true)
  })

  it('returns failure on non-ApiError', async () => {
    server.use(
      http.post('/api/remote/connect', () =>
        HttpResponse.error(),
      ),
    )
    const result = await testConnection(baseConfig)
    expect(result.success).toBe(false)
    expect(result.error).toBeDefined()
  })

  it('rethrows ApiError (e.g. host key confirmation)', async () => {
    server.use(
      http.post('/api/remote/connect', () =>
        HttpResponse.json({ detail: 'Host key changed' }, { status: 409 }),
      ),
    )
    await expect(testConnection(baseConfig)).rejects.toThrow(ApiError)
  })
})

describe('getLocalVersion', () => {
  it('returns version string', async () => {
    const ver = await getLocalVersion()
    expect(ver).toBe('0.1.0')
  })

  it('returns unknown when version not in response', async () => {
    server.use(
      http.get('/api/health', () => HttpResponse.json({ status: 'ok' })),
    )
    const ver = await getLocalVersion()
    expect(ver).toBe('unknown')
  })
})

describe('Known hosts', () => {
  it('listKnownHosts returns entries', async () => {
    server.use(
      http.get('/api/remote/known-hosts/list', () =>
        HttpResponse.json({ entries: [{ host: 'h', fingerprint: 'fp' }] }),
      ),
    )
    const entries = await listKnownHosts()
    expect(entries).toHaveLength(1)
  })

  it('listKnownHosts returns empty when no entries key', async () => {
    server.use(
      http.get('/api/remote/known-hosts/list', () =>
        HttpResponse.json({}),
      ),
    )
    const entries = await listKnownHosts()
    expect(entries).toEqual([])
  })

  it('removeKnownHost', async () => {
    server.use(
      http.post('/api/remote/known-hosts/remove', () =>
        HttpResponse.json({ ok: true, changed: true }),
      ),
    )
    const data = await removeKnownHost({ host: 'h', port: 22 })
    expect(data.ok).toBe(true)
  })

  it('acceptKnownHost', async () => {
    server.use(
      http.post('/api/remote/known-hosts/accept', () =>
        HttpResponse.json({ ok: true }),
      ),
    )
    const data = await acceptKnownHost({ host: 'h', port: 22, key_type: 'ssh-rsa', fingerprint: 'fp' })
    expect(data.ok).toBe(true)
  })
})

describe('Conda & remote config', () => {
  it('listCondaEnvs', async () => {
    server.use(
      http.get('/api/remote/conda-envs', () =>
        HttpResponse.json({ envs: ['base', 'myenv'] }),
      ),
    )
    const data = await listCondaEnvs('conn1')
    expect(data.envs).toHaveLength(2)
  })

  it('getEnvConfigs returns config map', async () => {
    server.use(
      http.get('/api/remote/env-configs', () =>
        HttpResponse.json({ configs: { base: { pythonVersion: '3.10' } } }),
      ),
    )
    const data = await getEnvConfigs('conn1')
    expect(data.base.pythonVersion).toBe('3.10')
  })

  it('getEnvConfigs returns empty when no configs key', async () => {
    server.use(
      http.get('/api/remote/env-configs', () =>
        HttpResponse.json({}),
      ),
    )
    const data = await getEnvConfigs('conn1')
    expect(data).toEqual({})
  })

  it('getRemoteConfig', async () => {
    server.use(
      http.get('/api/remote/config', () =>
        HttpResponse.json({ storage: '/data' }),
      ),
    )
    const data = await getRemoteConfig('conn1', 'myenv')
    expect(data.storage).toBe('/data')
  })
})

describe('quickStartRemoteViewer', () => {
  it('throws when remoteRoot is missing', async () => {
    await expect(quickStartRemoteViewer(baseConfig)).rejects.toThrow(
      'Remote storage root is required',
    )
  })

  it('returns session from nested result.session', async () => {
    server.use(
      http.post('/api/remote/viewer/start', () =>
        HttpResponse.json({ ok: true, session: { sessionId: 's2', status: 'running' } }),
      ),
    )
    const session = await quickStartRemoteViewer({ ...baseConfig, remoteRoot: '/data' })
    expect(session.sessionId).toBe('s2')
  })

  it('falls back to raw result when session key missing', async () => {
    server.use(
      http.post('/api/remote/viewer/start', () =>
        HttpResponse.json({ sessionId: 's3', status: 'running' }),
      ),
    )
    const session = await quickStartRemoteViewer({ ...baseConfig, remoteRoot: '/data' })
    expect(session.sessionId).toBe('s3')
  })
})

describe('error message parsing edge cases', () => {
  it('uses detail.message when detail is object with message', async () => {
    server.use(
      http.post('/api/remote/connect', () =>
        HttpResponse.json({ detail: { message: 'custom error' } }, { status: 500 }),
      ),
    )
    await expect(connectRemote(baseConfig)).rejects.toThrow('custom error')
  })

  it('uses fallback when detail is empty string', async () => {
    server.use(
      http.post('/api/remote/connect', () =>
        HttpResponse.json({ detail: '  ' }, { status: 500 }),
      ),
    )
    await expect(connectRemote(baseConfig)).rejects.toThrow('Failed to connect to remote server')
  })

  it('handles non-JSON error response', async () => {
    server.use(
      http.post('/api/remote/connect', () =>
        new HttpResponse('plain text error', {
          status: 500,
          headers: { 'Content-Type': 'text/plain' },
        }),
      ),
    )
    await expect(connectRemote(baseConfig)).rejects.toThrow('plain text error')
  })

  it('handles empty response body', async () => {
    server.use(
      http.post('/api/remote/connect', () =>
        new HttpResponse(null, {
          status: 500,
          headers: { 'Content-Type': 'text/plain' },
        }),
      ),
    )
    await expect(connectRemote(baseConfig)).rejects.toThrow('Failed to connect to remote server')
  })
})
