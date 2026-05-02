import { expect, test } from '@playwright/test'

test('viewer main flow loads runs and opens run detail', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('i18nextLng', 'en')
  })

  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
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
      return route.fulfill({ json: { dismissed_alerts: [] } })
    }
    if (path === '/api/config/column-widths') {
      if (route.request().method() === 'POST') {
        return route.fulfill({ json: { ok: true } })
      }
      return route.fulfill({ json: { widths: {} } })
    }
    if (path === '/api/paths') {
      return route.fulfill({ json: { paths: [] } })
    }
    if (path === '/api/runs') {
      return route.fulfill({
        json: {
          runs: [
            {
              id: 'run_alpha',
              path: 'proj/train',
              alias: 'Baseline Alpha',
              tags: ['baseline'],
              status: 'finished',
              created_time: 1700000000,
              summary: {},
              assets_count: 2,
            },
          ],
        },
      })
    }
    if (path === '/api/runs/run_alpha') {
      return route.fulfill({
        json: {
          run_id: 'run_alpha',
          path: 'proj/train',
          alias: 'Baseline Alpha',
          status: 'finished',
          start_time: 1700000000,
          duration: 3600,
          pid: 4321,
          run_dir: '/tmp/run_alpha',
          logs: '/tmp/run_alpha/logs.txt',
          assets_count: 2,
          summary: { loss: 0.1 },
        },
      })
    }
    if (path === '/api/runs/run_alpha/metrics_step') {
      return route.fulfill({
        json: {
          columns: ['global_step', 'time', 'train_loss', 'val_loss'],
          rows: [
            { global_step: 1, time: 1700000010, train_loss: 0.8, val_loss: 1.0 },
            { global_step: 2, time: 1700000020, train_loss: 0.6, val_loss: 0.9 },
          ],
          total: 2,
        },
      })
    }
    if (path === '/api/runs/run_alpha/images') {
      return route.fulfill({ json: { run_id: 'run_alpha', images: [] } })
    }
    if (path === '/api/runs/run_alpha/assets') {
      return route.fulfill({ json: { assets: {} } })
    }
    if (path === '/api/runs/run_alpha/assets/refs') {
      return route.fulfill({
        json: {
          run_id: 'run_alpha',
          orphaned_assets: [],
          shared_assets: [],
          orphaned_count: 0,
          shared_count: 0,
        },
      })
    }
    if (path === '/api/storage/stats') {
      return route.fulfill({
        json: {
          storage_root: '/tmp/runicorn',
          total: { size_bytes: 0, size_human: '0 B' },
          archive: {
            size_bytes: 0,
            size_human: '0 B',
            blobs: { size_bytes: 0, size_human: '0 B', file_count: 0 },
            manifests: { size_bytes: 0, size_human: '0 B', file_count: 0, by_category: {} },
            outputs: { size_bytes: 0, size_human: '0 B', file_count: 0 },
          },
          runs: { size_bytes: 0, size_human: '0 B', projects_count: 1, experiments_count: 1, runs_count: 1 },
          index: { size_bytes: 0, size_human: '0 B' },
        },
      })
    }

    return route.fulfill({ json: {} })
  })

  await page.goto('/?lng=en')

  await expect(page.getByText('Experiments')).toBeVisible()
  await expect(page.getByText('proj/train')).toBeVisible()

  await page.getByRole('button', { name: 'View run details' }).click()

  await expect(page).toHaveURL(/\/runs\/run_alpha/)
  await expect(page.getByText('Baseline Alpha')).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Overview' })).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Live Logs' })).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Assets' })).toBeVisible()
})
