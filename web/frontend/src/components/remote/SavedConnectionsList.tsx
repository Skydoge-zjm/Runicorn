/**
 * Saved Connections List Component
 * 
 * Displays and manages saved SSH connection configurations
 */

import React from 'react'
import {
  Card,
  List,
  Button,
  Space,
  Avatar,
  Typography,
  Empty,
  Modal,
  message
} from 'antd'
import {
  CloudServerOutlined,
  ThunderboltOutlined,
  EditOutlined,
  DeleteOutlined,
  LinkOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { SavedConnection } from '../../types/remote'

const { Text } = Typography

interface SavedConnectionsListProps {
  connections: SavedConnection[]
  onQuickStart: (connection: SavedConnection) => Promise<void>
  onConnect?: (connection: SavedConnection) => Promise<void>
  onEdit?: (connection: SavedConnection) => void
  onDelete: (id: string) => void
  loading?: boolean
}

export default function SavedConnectionsList({
  connections,
  onQuickStart,
  onConnect,
  onEdit,
  onDelete,
  loading = false
}: SavedConnectionsListProps) {
  const { t } = useTranslation()

  const handleQuickStart = async (conn: SavedConnection) => {
    try {
      await onQuickStart(conn)
      message.success(t('remote.message.viewerStarted'))
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.message.viewerStartFailed'))
    }
  }

  const handleConnect = async (conn: SavedConnection) => {
    if (!onConnect) return
    try {
      await onConnect(conn)
      // Success message is handled in the parent component
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.message.connectFailed'))
    }
  }

  const handleDelete = (conn: SavedConnection) => {
    Modal.confirm({
      title: t('remote.message.confirmDelete'),
      content: conn.name,
      okText: t('remote.saved.delete'),
      okButtonProps: { danger: true },
      onOk: () => {
        onDelete(conn.id)
        message.success(t('remote.message.configDeleted'))
      }
    })
  }

  if (connections.length === 0) {
    return (
      <Card title={t('remote.saved.title')}>
        <Empty
          description={
            <Space direction="vertical">
              <Text type="secondary">{t('remote.saved.empty')}</Text>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {t('remote.saved.emptyHint')}
              </Text>
            </Space>
          }
        />
      </Card>
    )
  }

  return (
    <Card title={t('remote.saved.title')}>
      <List
        dataSource={connections}
        loading={loading}
        renderItem={conn => (
          <List.Item
            actions={[
              <Button
                key="quickstart"
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={() => handleQuickStart(conn)}
                size="small"
              >
                {t('remote.saved.quickStart')}
              </Button>,
              onConnect && (
                <Button
                  key="connect"
                  icon={<LinkOutlined />}
                  onClick={() => handleConnect(conn)}
                  size="small"
                >
                  {t('remote.saved.connectOnly')}
                </Button>
              ),
              <Button
                key="delete"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(conn)}
                size="small"
              >
                {t('remote.saved.delete')}
              </Button>
            ].filter(Boolean)}
          >
            <List.Item.Meta
              avatar={
                <Avatar 
                  icon={<CloudServerOutlined />}
                  style={{ backgroundColor: '#1677ff' }}
                />
              }
              title={<Text strong>{conn.name}</Text>}
              description={
                <Space direction="vertical" size={0}>
                  <Text type="secondary">
                    {conn.username}@{conn.host}:{conn.port}
                  </Text>
                  <Text type="secondary" code style={{ fontSize: '12px' }}>
                    {conn.remoteRoot}
                  </Text>
                  <Text type="secondary" style={{ fontSize: '11px' }}>
                    {conn.authMethod === 'password' ? 'Password Auth' : `Key Auth (${conn.privateKeyPath})`}
                  </Text>
                </Space>
              }
            />
          </List.Item>
        )}
      />
    </Card>
  )
}
