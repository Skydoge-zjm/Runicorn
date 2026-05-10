import { Input, Modal, Space, Typography } from 'antd'
import { useTranslation } from 'react-i18next'

import type { SavedConnectionProfile, SavedServer } from '../../types/remote'

const { Text } = Typography

type Props = {
  open: boolean
  loading: boolean
  profile: SavedConnectionProfile | null
  server: SavedServer | null
  password: string
  onChangePassword: (value: string) => void
  onSubmit: () => void
  onCancel: () => void
}

export default function PasswordPromptModal({
  open,
  loading,
  profile,
  server,
  password,
  onChangePassword,
  onSubmit,
  onCancel,
}: Props) {
  const { t } = useTranslation()

  return (
    <Modal
      title={t('remote.form.enterPassword')}
      open={open}
      onOk={onSubmit}
      onCancel={onCancel}
      okText={t('remote.form.connectButton')}
      cancelText={t('remote.form.cancel')}
      confirmLoading={loading}
      centered
      width={400}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Text>
          {t('remote.form.connectionTo')}: <Text strong>{profile?.name}</Text>
        </Text>
        <Text type="secondary">
          {server?.username}@{server?.host}
        </Text>
        <Input.Password
          placeholder={t('remote.form.password')}
          value={password}
          onChange={e => onChangePassword(e.target.value)}
          onPressEnter={onSubmit}
          autoFocus
          size="large"
        />
      </Space>
    </Modal>
  )
}

