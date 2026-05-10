import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './helpers'
import RemoteViewerPage from '../pages/RemoteViewerPage'
import type { SavedConnectionProfile, SavedServer } from '../types/remote'

const refetchSessions = vi.fn()
const startRemoteViewer = vi.fn()

vi.mock('../utils/logger', () => ({
  default: { error: vi.fn(), warn: vi.fn(), info: vi.fn(), debug: vi.fn() },
}))

vi.mock('../api/remote', () => ({
  connectRemote: vi.fn(),
  listCondaEnvs: vi.fn(),
  getRemoteConfig: vi.fn(),
  listRemoteStorageCandidates: vi.fn(),
  startRemoteViewer: (...args: any[]) => startRemoteViewer(...args),
  stopRemoteViewer: vi.fn(),
  disconnectRemote: vi.fn(),
  acceptKnownHost: vi.fn(),
  listKnownHosts: vi.fn(),
  removeKnownHost: vi.fn(),
}))

vi.mock('../hooks/useRemoteSessions', () => ({
  useRemoteSessions: () => ({
    sessions: [
      {
        sessionId: 'existing-session',
        host: 'gpu.example.com',
        sshPort: 22,
        username: 'runner',
        localPort: 9000,
        remotePort: 23300,
        remoteRoot: '/existing',
        status: 'running',
        startedAt: 1,
      },
    ],
    loading: false,
    error: null,
    refetch: refetchSessions,
  }),
}))

const server: SavedServer = {
  kind: 'server',
  id: 'srv_runner_gpu_example_com_22',
  name: 'runner@gpu.example.com:22',
  host: 'gpu.example.com',
  port: 22,
  username: 'runner',
  authMethod: 'password',
  password: 'secret',
  hasSavedPassword: true,
  createdAt: 1,
}

const profile: SavedConnectionProfile = {
  kind: 'connection',
  id: 'profile-1',
  serverId: server.id,
  name: 'Main profile',
  condaEnv: 'torch',
  remoteRoot: '/data/runicorn',
  localPort: 9000,
  remotePort: 22,
  createdAt: 1,
}

vi.mock('../hooks/useSavedConnections', () => ({
  useSavedConnections: () => ({
    servers: [server],
    getProfilesForServer: (serverId: string) => (serverId === server.id ? [profile] : []),
    addServer: vi.fn(),
    updateServer: vi.fn(),
    deleteServer: vi.fn(),
    addProfile: vi.fn(),
    updateProfile: vi.fn(),
    deleteProfile: vi.fn(),
  }),
}))

vi.mock('../components/remote/RemoteSessionCard', () => ({
  default: ({ session }: any) => <div data-testid={`session-${session.sessionId}`}>{session.sessionId}</div>,
}))

vi.mock('../components/remote/HostKeyModal', () => ({
  default: () => null,
}))

vi.mock('../pages/remote-viewer/KnownHostsDrawer', () => ({
  default: () => null,
}))

vi.mock('../pages/remote-viewer/PasswordPromptModal', () => ({
  default: () => null,
}))

vi.mock('../pages/remote-viewer/RemoteViewerOverview', () => ({
  default: () => <div data-testid="remote-overview" />,
}))

vi.mock('../pages/remote-viewer/RemoteWizardModal', () => ({
  default: () => null,
}))

vi.mock('../pages/remote-viewer/SavedServersPanel', () => ({
  default: ({ servers, getProfilesForServer, onQuickStartProfile }: any) => {
    const firstServer = servers[0]
    const firstProfile = getProfilesForServer(firstServer.id)[0]
    return (
      <button type="button" onClick={() => onQuickStartProfile(firstServer.id, firstProfile)}>
        quick-start-profile
      </button>
    )
  },
}))

describe('RemoteViewerPage', () => {
  beforeEach(() => {
    startRemoteViewer.mockResolvedValue({ sessionId: 'new-session', status: 'running' })
  })

  it('quick start uses current remote API path inputs and clears conflicting saved ports', async () => {
    renderWithProviders(<RemoteViewerPage />)

    await userEvent.click(screen.getByRole('button', { name: 'quick-start-profile' }))

    await waitFor(() => {
      expect(startRemoteViewer).toHaveBeenCalledTimes(1)
    })

    expect(startRemoteViewer).toHaveBeenCalledWith({
      host: 'gpu.example.com',
      port: 22,
      username: 'runner',
      authMethod: 'password',
      savedServerId: 'srv_runner_gpu_example_com_22',
      password: 'secret',
      privateKeyPath: undefined,
      passphrase: undefined,
      condaEnv: 'torch',
      remoteRoot: '/data/runicorn',
      localPort: undefined,
      remotePort: undefined,
    })
    expect(refetchSessions).toHaveBeenCalledTimes(1)
  })
})
