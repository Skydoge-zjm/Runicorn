/**
 * Remote Session Card Component
 * 
 * Displays information about an active Remote Viewer session
 */

import {
  Card,
  Space,
  Button,
  Descriptions,
  Alert,
  Typography,
  App,
  theme
} from 'antd'
import {
  LinkOutlined,
  StopOutlined,
  DisconnectOutlined,
  CloudServerOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import type { RemoteSession } from '../../types/remote'
import ServerStatusLight from '../fancy/ServerStatusLight'
import { openInTauriWindow } from '../../utils/tauri'

dayjs.extend(relativeTime)

const { Text } = Typography

interface RemoteSessionCardProps {
  session: RemoteSession
  onOpen?: (session: RemoteSession) => void
  onStop?: (session: RemoteSession) => Promise<void>
  onDisconnect?: (session: RemoteSession) => Promise<void>
}

const statusMessageMap: Record<string, string> = {
  connecting: 'Establishing connection...',
  running: 'Remote Viewer is running and accessible',
  stopping: 'Stopping Remote Viewer...',
  stopped: 'Remote Viewer has been stopped',
  error: 'An error occurred'
}

export default function RemoteSessionCard({
  session,
  onOpen,
  onStop,
  onDisconnect
}: RemoteSessionCardProps) {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const { modal } = App.useApp()

  const handleOpen = () => {
    const url = `http://localhost:${session.localPort}`
    const label = `remote-${session.sessionId}`
    const title = `Runicorn Remote — ${session.host}`
    openInTauriWindow(url, label, title)
    onOpen?.(session)
  }

  const handleStop = async () => {
    if (onStop) {
      try {
        await onStop(session)
      } catch (error) {
        // Error handling is done in parent component
      }
    }
  }

  const handleDisconnect = () => {
    modal.confirm({
      title: t('remote.message.confirmDisconnect'),
      content: `${session.host}:${session.remotePort}`,
      onOk: async () => {
        if (onDisconnect) {
          await onDisconnect(session)
        }
      }
    })
  }

  return (
    <Card
      title={
        <Space>
          <CloudServerOutlined />
          <Text strong>{session.host}</Text>
          <ServerStatusLight 
            status={
              session.status === 'running' ? 'online' : 
              session.status === 'connecting' || session.status === 'stopping' ? 'connecting' : 
              'offline'
            } 
            label={t(`remote.status.${session.status}`)}
          />
        </Space>
      }
      extra={
        <Space>
          <Button
            type="primary"
            icon={<LinkOutlined />}
            onClick={handleOpen}
            disabled={session.status !== 'running'}
          >
            {t('remote.session.open')}
          </Button>
          <Button
            icon={<StopOutlined />}
            onClick={handleStop}
            disabled={session.status !== 'running'}
          >
            {t('remote.session.stop')}
          </Button>
          <Button
            danger
            icon={<DisconnectOutlined />}
            onClick={handleDisconnect}
          >
            {t('remote.session.disconnect')}
          </Button>
        </Space>
      }
      style={{ marginBottom: 16 }}
    >
      <Descriptions column={2} size="small">
        <Descriptions.Item label={t('remote.session.localAccess')}>
          <a
            href={`http://localhost:${session.localPort}`}
            onClick={(e) => {
              e.preventDefault()
              handleOpen()
            }}
          >
            http://localhost:{session.localPort}
          </a>
        </Descriptions.Item>
        <Descriptions.Item label={t('remote.session.remotePath')}>
          <Text code>{session.remoteRoot}</Text>
        </Descriptions.Item>
        <Descriptions.Item label={t('remote.session.sshPort')}>
          {session.sshPort}
        </Descriptions.Item>
        <Descriptions.Item label={t('remote.session.remotePort')}>
          {session.remotePort}
        </Descriptions.Item>
        <Descriptions.Item label={t('remote.session.remotePid')}>
          {session.remotePid || 'N/A'}
        </Descriptions.Item>
        <Descriptions.Item label={t('remote.session.startedAt')}>
          {dayjs(session.startedAt).fromNow()}
        </Descriptions.Item>
      </Descriptions>

      {/* Status Alert */}
      <Alert
        type={session.status === 'running' ? 'success' : session.status === 'error' ? 'error' : 'info'}
        message={statusMessageMap[session.status] || session.status}
        description={session.error}
        showIcon
        style={{ marginTop: 16 }}
      />

      {/* Session Details */}
      <div style={{ marginTop: 16, fontSize: 12 }}>
        <Text type="secondary">Session ID: {session.sessionId}</Text>
      </div>
    </Card>
  )
}
