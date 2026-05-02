import { expect, test } from '@playwright/test'

test('remote page renders saved connections and quick start session', async ({ page }) => {
  let sessions = [] as Array<Record<string, unknown>>
  let savedEntries = [
    {
      kind: 'server',
      id: 'srv_ml_gpu_lab_22',
      name: 'GPU Lab',
      host: 'gpu-lab',
      port: 22,
      username: 'ml',
      authMethod: 'key',
      privateKeyPath: '~/.ssh/id_rsa',
      hasSavedPassword: false,
      hasSavedPrivateKey: true,
      hasSavedPassphrase: false,
      createdAt: 1700000000000,
    },
    {
      kind: 'connection',
      id: 'profile_train',
      serverId: 'srv_ml_gpu_lab_22',
      name: 'Training Env',
      condaEnv: 'runicorn_dev',
      remoteRoot: '/data/runicorn',
      localPort: 23300,
      remotePort: 23300,
      createdAt: 1700000001000,
    },
  ]

  await page.addInitScript(() => {
    localStorage.setItem('i18nextLng', 'en')
  })

  await page.route('**/*', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    if (!path.startsWith('/api/')) {
      return route.continue()
    }

    if (path === '/api/health') {
      return route.fulfill({ json: { status: 'ok', version: '0.7.0' } })
    }
    if (path === '/api/config') {
      return route.fulfill({
        json: {
          user_root_dir: '/tmp/runicorn',
          storage: '/tmp/runicorn',
          home_directory: '/tmp',
          storage_backend: { mode: 'sqlite', label: 'SQLite-backed', available: true },
        },
      })
    }
    if (path === '/api/config/dismissed-alerts') {
      if (request.method() === 'POST') {
        return route.fulfill({ json: { ok: true } })
      }
      return route.fulfill({ json: { dismissed_alerts: [] } })
    }
    if (path === '/api/remote/connections/saved') {
      if (request.method() === 'POST') {
        savedEntries = JSON.parse(request.postData() || '[]')
        return route.fulfill({ json: { ok: true } })
      }
      return route.fulfill({ json: { connections: savedEntries } })
    }
    if (path === '/api/remote/viewer/sessions') {
      return route.fulfill({ json: { sessions } })
    }
    if (path === '/api/remote/viewer/start') {
      sessions = [
        {
          sessionId: 'sess-1',
          host: 'gpu-lab',
          sshPort: 22,
          localPort: 23300,
          remotePort: 23300,
          remoteRoot: '/data/runicorn',
          remotePid: 7788,
          status: 'running',
          startedAt: new Date('2026-04-27T12:00:00Z').toISOString(),
        },
      ]
      return route.fulfill({ json: sessions[0] })
    }
    if (path === '/api/remote/viewer/stop') {
      sessions = []
      return route.fulfill({ json: { ok: true } })
    }

    return route.fulfill({ json: {} })
  })

  await page.goto('/remote?lng=en')

  await expect(page.getByText('Remote Viewer')).toBeVisible()
  await expect(page.getByText('Saved Connections')).toBeVisible()
  await expect(page.getByText('GPU Lab')).toBeVisible()
  await page.getByText('GPU Lab').click()
  await expect(page.getByText('Training Env')).toBeVisible()

  await page.getByRole('button', { name: 'Quick Start' }).click()

  await expect(page.getByText('http://localhost:23300')).toBeVisible()
  await expect(page.getByText('Remote Viewer is running and accessible')).toBeVisible()
})
