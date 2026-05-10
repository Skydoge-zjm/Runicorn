import { Button, Card, Collapse, Empty, List, Popconfirm, Space, Tag, Tooltip, Typography } from 'antd'
import { CloudServerOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

import type { SavedConnectionProfile, SavedServer } from '../../types/remote'

const { Text } = Typography

type Props = {
  servers: SavedServer[]
  getProfilesForServer: (serverId: string) => SavedConnectionProfile[]
  quickStartingProfileId: string | null
  onAddServer: () => void
  onAddConnection: (serverId: string) => void
  onQuickStartProfile: (serverId: string, profile: SavedConnectionProfile) => void
  onEditProfile: (serverId: string, profileId: string) => void
  onDeleteServer: (serverId: string) => void
  onDeleteProfile: (profileId: string) => void
}

export default function SavedServersPanel({
  servers,
  getProfilesForServer,
  quickStartingProfileId,
  onAddServer,
  onAddConnection,
  onQuickStartProfile,
  onEditProfile,
  onDeleteServer,
  onDeleteProfile,
}: Props) {
  const { t } = useTranslation()

  return (
    <Card
      title={t('remote.saved.title')}
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={onAddServer}>
          {t('remote.saved.addServer')}
        </Button>
      }
      style={{ minHeight: 520 }}
    >
      {servers.length === 0 ? (
        <Empty description={t('remote.saved.noServers')} />
      ) : (
        <Collapse accordion>
          {servers.map(server => (
            <Collapse.Panel
              header={
                <Space direction="vertical" size={0}>
                  <Text strong>{server.name}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    SSH {server.username}@{server.host}:{server.port}
                  </Text>
                </Space>
              }
              key={server.id}
              extra={
                <Space>
                  <Button
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={(event) => {
                      event.stopPropagation()
                      onAddConnection(server.id)
                    }}
                  >
                    {t('remote.saved.addConnection')}
                  </Button>
                  <Popconfirm
                    title={t('remote.message.confirmDelete')}
                    onConfirm={() => onDeleteServer(server.id)}
                    okButtonProps={{ danger: true }}
                  >
                    <Button
                      size="small"
                      danger
                      onClick={(event) => event.stopPropagation()}
                    >
                      {t('remote.saved.delete')}
                    </Button>
                  </Popconfirm>
                </Space>
              }
            >
              <List
                size="small"
                dataSource={getProfilesForServer(server.id)}
                locale={{ emptyText: t('remote.saved.noConnections') }}
                renderItem={(profile) => (
                  <List.Item
                    style={{ paddingTop: '0.375rem', paddingBottom: '0.375rem' }}
                    actions={[
                      <Button
                        key="quickstart"
                        type="primary"
                        icon={<ThunderboltOutlined />}
                        size="small"
                        loading={quickStartingProfileId === profile.id}
                        disabled={quickStartingProfileId !== null && quickStartingProfileId !== profile.id}
                        onClick={() => onQuickStartProfile(server.id, profile)}
                      >
                        {t('remote.saved.quickStart')}
                      </Button>,
                      <Button
                        key="edit"
                        size="small"
                        onClick={() => onEditProfile(server.id, profile.id)}
                      >
                        {t('remote.saved.edit')}
                      </Button>,
                      <Popconfirm
                        key="delete"
                        title={t('remote.message.confirmDelete')}
                        onConfirm={() => onDeleteProfile(profile.id)}
                        okButtonProps={{ danger: true }}
                      >
                        <Button danger size="small">
                          {t('remote.saved.delete')}
                        </Button>
                      </Popconfirm>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Text
                          strong
                          style={{ lineHeight: '20px', display: 'block', marginBottom: 2 }}
                          ellipsis={{ tooltip: profile.name }}
                        >
                          {profile.name}
                        </Text>
                      }
                      description={
                        <div
                          style={{
                            display: 'grid',
                            gridTemplateColumns: 'clamp(6.5rem, 28%, 12rem) minmax(0, 1fr) auto',
                            alignItems: 'center',
                            gap: 6,
                            minWidth: 0,
                            lineHeight: '18px',
                          }}
                        >
                          <Tooltip title={profile.condaEnv || 'system'}>
                            <Tag
                              color="blue"
                              style={{
                                marginInlineEnd: 0,
                                fontSize: 11,
                                lineHeight: '16px',
                                paddingInline: 6,
                                maxWidth: '100%',
                              }}
                            >
                              <Text
                                style={{ maxWidth: '100%', display: 'inline-block', verticalAlign: 'top' }}
                                ellipsis
                              >
                                {profile.condaEnv || 'system'}
                              </Text>
                            </Tag>
                          </Tooltip>

                          <Text
                            type="secondary"
                            code
                            style={{
                              fontSize: 11,
                              lineHeight: '16px',
                              minWidth: 0,
                              display: 'inline-block',
                            }}
                            ellipsis={{ tooltip: profile.remoteRoot || '-' }}
                          >
                            {profile.remoteRoot || '-'}
                          </Text>

                          <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end', flexWrap: 'nowrap' }}>
                            {(profile.localPort !== undefined || profile.remotePort !== undefined) && (
                              <>
                                <Tag style={{ marginInlineEnd: 0, fontSize: 11, lineHeight: '16px', paddingInline: 6 }}>
                                  L:{profile.localPort ?? 'auto'}
                                </Tag>
                                <Tag style={{ marginInlineEnd: 0, fontSize: 11, lineHeight: '16px', paddingInline: 6 }}>
                                  R:{profile.remotePort ?? 'auto'}
                                </Tag>
                              </>
                            )}
                          </div>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            </Collapse.Panel>
          ))}
        </Collapse>
      )}
    </Card>
  )
}

