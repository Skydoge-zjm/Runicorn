import { Button, Drawer, Popconfirm, Table, Typography } from 'antd'
import { useTranslation } from 'react-i18next'

import type { KnownHostsEntry } from '../../types/remote'

const { Text } = Typography

type Props = {
  open: boolean
  knownHosts: KnownHostsEntry[]
  loading: boolean
  onClose: () => void
  onRefresh: () => void
  onRemove: (entry: KnownHostsEntry) => void
}

export default function KnownHostsDrawer({
  open,
  knownHosts,
  loading,
  onClose,
  onRefresh,
  onRemove,
}: Props) {
  const { t } = useTranslation()

  return (
    <Drawer
      title={t('remote.knownHosts.title')}
      open={open}
      onClose={onClose}
      width={860}
    >
      <Button onClick={onRefresh} loading={loading} style={{ marginBottom: 12 }}>
        {t('remote.knownHosts.refresh')}
      </Button>
      <Table
        dataSource={knownHosts}
        loading={loading}
        rowKey={record => `${record.known_hosts_host}-${record.key_type}`}
        pagination={false}
        locale={{ emptyText: t('remote.knownHosts.empty') }}
        columns={[
          {
            title: t('remote.form.host'),
            dataIndex: 'host',
            key: 'host',
            render: (text: string, record: KnownHostsEntry) => (
              <Text code>{record.known_hosts_host || `${text}:${record.port}`}</Text>
            ),
          },
          {
            title: t('remote.hostKey.keyType'),
            dataIndex: 'key_type',
            key: 'key_type',
            render: (text: string) => <Text code>{text}</Text>,
          },
          {
            title: t('remote.hostKey.fingerprint'),
            dataIndex: 'fingerprint_sha256',
            key: 'fingerprint_sha256',
            render: (text: string) => <Text code copyable>{text}</Text>,
          },
          {
            title: t('remote.knownHosts.actions'),
            key: 'actions',
            render: (_: unknown, record: KnownHostsEntry) => (
              <Popconfirm
                title={t('remote.knownHosts.removeConfirm')}
                onConfirm={() => onRemove(record)}
                okButtonProps={{ danger: true }}
              >
                <Button danger size="small">
                  {t('remote.knownHosts.remove')}
                </Button>
              </Popconfirm>
            ),
          },
        ]}
      />
    </Drawer>
  )
}

