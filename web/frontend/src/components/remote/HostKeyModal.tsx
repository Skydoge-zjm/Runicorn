import React from 'react'
import { Alert, Descriptions, Modal, Space, Typography } from 'antd'
import { useTranslation } from 'react-i18next'

import type { HostKeyInfo } from '../../types/remote'

const { Paragraph, Text } = Typography

interface HostKeyModalProps {
  open: boolean
  loading?: boolean
  target?: string
  hostKey?: HostKeyInfo
  onConfirm: () => void
  onCancel: () => void
}

export default function HostKeyModal({
  open,
  loading = false,
  target,
  hostKey,
  onConfirm,
  onCancel
}: HostKeyModalProps) {
  const { t } = useTranslation()

  const reason = hostKey?.reason
  const isChanged = reason === 'changed'

  const alertMessage = isChanged
    ? t('remote.hostKey.reasonChanged')
    : t('remote.hostKey.reasonUnknown')

  const showExpected = isChanged && (hostKey?.expected_fingerprint_sha256 || hostKey?.expected_public_key)

  return (
    <Modal
      title={t('remote.hostKey.title')}
      open={open}
      onOk={onConfirm}
      onCancel={onCancel}
      okText={t('remote.hostKey.trustAndContinue')}
      cancelText={t('remote.hostKey.cancel')}
      okButtonProps={{ danger: isChanged }}
      confirmLoading={loading}
      centered
      width={760}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert type={isChanged ? 'warning' : 'info'} message={alertMessage} showIcon />

        {target && (
          <Text>
            {t('remote.hostKey.target')}: <Text strong>{target}</Text>
          </Text>
        )}

        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label={t('remote.form.host')}>
            <Text code>{hostKey?.host}</Text>
          </Descriptions.Item>
          <Descriptions.Item label={t('remote.form.port')}>{hostKey?.port}</Descriptions.Item>
          <Descriptions.Item label={t('remote.hostKey.keyType')}>
            <Text code>{hostKey?.key_type}</Text>
          </Descriptions.Item>
          <Descriptions.Item label={t('remote.hostKey.fingerprint')}>
            <Text code copyable>
              {hostKey?.fingerprint_sha256}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label={t('remote.hostKey.publicKey')}>
            <Paragraph
              style={{ marginBottom: 0 }}
              copyable
              ellipsis={{ rows: 2, expandable: true, symbol: t('remote.hostKey.expand') }}
            >
              <Text code>{hostKey?.public_key}</Text>
            </Paragraph>
          </Descriptions.Item>
        </Descriptions>

        {showExpected && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label={t('remote.hostKey.expectedFingerprint')}>
              <Text code copyable>
                {hostKey?.expected_fingerprint_sha256}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label={t('remote.hostKey.expectedPublicKey')}>
              <Paragraph
                style={{ marginBottom: 0 }}
                copyable
                ellipsis={{ rows: 2, expandable: true, symbol: t('remote.hostKey.expand') }}
              >
                <Text code>{hostKey?.expected_public_key}</Text>
              </Paragraph>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Space>
    </Modal>
  )
}
