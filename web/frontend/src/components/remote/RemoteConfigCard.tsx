/**
 * Remote Config Card Component
 * 
 * Displays remote server configuration for user confirmation
 */

import React from 'react'
import {
  Card,
  Descriptions,
  Alert,
  Space,
  Button,
  Tag,
  Typography,
  Input,
  Form
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
  EditOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { RemoteConfig, SSHConnectionConfig } from '../../types/remote'

const { Text, Title } = Typography

interface RemoteConfigCardProps {
  config: RemoteConfig
  sshConfig: SSHConnectionConfig
  onConfirm: (remoteRoot: string, localPort?: number) => void
  onCancel: () => void
  loading?: boolean
}

export default function RemoteConfigCard({
  config,
  sshConfig,
  onConfirm,
  onCancel,
  loading = false
}: RemoteConfigCardProps) {
  const { t } = useTranslation()
  const [form] = Form.useForm()

  const handleConfirm = async () => {
    const values = await form.validateFields()
    onConfirm(values.remoteRoot, values.localPort)
  }

  return (
    <Card
      title={
        <Space>
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
          <span>{t('remote.config.title')}</span>
        </Space>
      }
    >
      {/* Server Info */}
      <Alert
        message={t('remote.config.connected')}
        description={`${sshConfig.username}@${sshConfig.host}:${sshConfig.port}`}
        type="success"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* Remote Configuration */}
      <Descriptions column={2} size="small" bordered style={{ marginBottom: 16 }}>
        <Descriptions.Item label={t('remote.config.pythonVersion')}>
          <Text code>{config.pythonVersion}</Text>
        </Descriptions.Item>
        <Descriptions.Item label={t('remote.config.runicornVersion')}>
          <Tag color="blue">{config.runicornVersion}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label={t('remote.config.storageRoot')} span={2}>
          <Space>
            <Text code>{config.defaultStorageRoot}</Text>
            {config.storageRootExists ? (
              <Tag icon={<CheckCircleOutlined />} color="success">
                {t('remote.config.exists')}
              </Tag>
            ) : (
              <Tag icon={<CloseCircleOutlined />} color="warning">
                {t('remote.config.notExists')}
              </Tag>
            )}
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label={t('remote.config.suggestedPort')}>
          {config.suggestedRemotePort}
        </Descriptions.Item>
      </Descriptions>

      {!config.storageRootExists && (
        <Alert
          message={t('remote.config.pathNotExistsWarning')}
          description={t('remote.config.pathNotExistsHint')}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Configuration Form */}
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          remoteRoot: config.defaultStorageRoot,
          localPort: sshConfig.localPort,
          remotePort: config.suggestedRemotePort
        }}
      >
        <Form.Item
          label={t('remote.config.confirmStorageRoot')}
          name="remoteRoot"
          rules={[{ required: true, message: 'Please enter remote storage root' }]}
        >
          <Input placeholder="/data/runicorn" />
        </Form.Item>

        <Form.Item
          label={t('remote.form.localPort')}
          name="localPort"
          help={t('remote.form.localPortHelp')}
        >
          <Input type="number" placeholder="23301" />
        </Form.Item>
      </Form>

      {/* Action Buttons */}
      <Space style={{ marginTop: 16 }}>
        <Button
          type="primary"
          icon={<ThunderboltOutlined />}
          onClick={handleConfirm}
          loading={loading}
          size="large"
        >
          {t('remote.config.startViewer')}
        </Button>
        <Button onClick={onCancel} disabled={loading}>
          {t('remote.form.cancel')}
        </Button>
      </Space>
    </Card>
  )
}
