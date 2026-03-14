/**
 * Remote Config Card Component
 * 
 * Displays remote server configuration for user confirmation
 */

import {
  Card,
  Descriptions,
  Alert,
  Space,
  Button,
  Tag,
  Typography,
  Input,
  InputNumber,
  Form,
  Divider,
  theme
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SaveOutlined,
  FolderOpenOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type {
  RemoteConfig,
  RemoteStorageCandidate,
  SSHConnectionConfig
} from '../../types/remote'
import DismissibleAlert from '../DismissibleAlert'

const { Text } = Typography

interface RemoteConfigCardProps {
  config: RemoteConfig
  sshConfig: SSHConnectionConfig
  onConfirm: (profileName: string, remoteRoot: string, localPort?: number, remotePort?: number) => void
  onCancel: () => void
  onDetectStorageCandidates: (scanRoot: string, maxDepth: number) => void
  storageCandidates?: RemoteStorageCandidate[]
  storageCandidatesLoading?: boolean
  storageCandidatesRequested?: boolean
  loading?: boolean
}

export default function RemoteConfigCard({
  config,
  sshConfig,
  onConfirm,
  onCancel,
  onDetectStorageCandidates,
  storageCandidates = [],
  storageCandidatesLoading = false,
  storageCandidatesRequested = false,
  loading = false
}: RemoteConfigCardProps) {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const [form] = Form.useForm()
  const selectedRemoteRoot = Form.useWatch('remoteRoot', form)

  const defaultScanRoot = config.homeDirectory || (() => {
    const idx = config.defaultStorageRoot.lastIndexOf('/')
    if (idx > 0) return config.defaultStorageRoot.slice(0, idx)
    return config.defaultStorageRoot
  })()

  const handleConfirm = async () => {
    const values = await form.validateFields()

    const localPort =
      values.localPort === undefined || values.localPort === null || values.localPort === ''
        ? undefined
        : Number(values.localPort)
    const remotePort =
      values.remotePort === undefined || values.remotePort === null || values.remotePort === ''
        ? undefined
        : Number(values.remotePort)

    onConfirm(values.profileName, values.remoteRoot, localPort, remotePort)
  }

  const handleDetect = async () => {
    const values = await form.validateFields(['scanRoot', 'scanDepth'])
    onDetectStorageCandidates(values.scanRoot, Number(values.scanDepth))
  }

  return (
    <Card
      title={
        <Space>
          <CheckCircleOutlined style={{ color: token.colorSuccess }} />
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
        <DismissibleAlert
          alertId="remote.config.pathNotExists"
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
          profileName:
            sshConfig.saveName ||
            `${sshConfig.condaEnv || 'system'} - ${(sshConfig.remoteRoot || config.defaultStorageRoot)}`,
          remoteRoot: sshConfig.remoteRoot || config.defaultStorageRoot,
          scanRoot: defaultScanRoot,
          scanDepth: 3,
          localPort: sshConfig.localPort,
          remotePort: sshConfig.remotePort || config.suggestedRemotePort
        }}
      >
        <Form.Item
          label={t('remote.profile.name')}
          name="profileName"
          rules={[{ required: true, message: t('remote.form.required') }]}
        >
          <Input placeholder={t('remote.profile.namePlaceholder')} />
        </Form.Item>

        <Form.Item label={t('remote.config.detectedStorageRoots')}>
          <Space direction="vertical" size={10} style={{ width: '100%' }}>
            <Text type="secondary">
              {t('remote.config.detectedStorageRootsHint')}
            </Text>

            <Space.Compact style={{ width: '100%' }}>
              <Form.Item
                name="scanRoot"
                rules={[{ required: true, message: t('remote.form.required') }]}
                style={{ flex: 1, marginBottom: 0 }}
              >
                <Input placeholder={t('remote.config.scanRootPlaceholder')} />
              </Form.Item>
              <Form.Item
                name="scanDepth"
                rules={[{ required: true, message: t('remote.form.required') }]}
                style={{ width: 120, marginBottom: 0 }}
              >
                <InputNumber
                  min={1}
                  max={8}
                  style={{ width: '100%' }}
                  addonBefore={t('remote.config.scanDepth')}
                />
              </Form.Item>
            </Space.Compact>

            <Button
              icon={<SearchOutlined />}
              onClick={() => void handleDetect()}
              loading={storageCandidatesLoading}
            >
              {t('remote.config.detectAction')}
            </Button>

            {storageCandidatesLoading ? (
              <Text type="secondary">{t('remote.config.detectingStorageRoots')}</Text>
            ) : storageCandidates.length > 0 ? (
              storageCandidates.map(candidate => {
                const active = candidate.path === selectedRemoteRoot
                return (
                  <Button
                    key={candidate.path}
                    block
                    type={active ? 'primary' : 'default'}
                    icon={<FolderOpenOutlined />}
                    onClick={() => form.setFieldValue('remoteRoot', candidate.path)}
                    style={{
                      height: 'auto',
                      justifyContent: 'space-between',
                      paddingBlock: 10,
                    }}
                  >
                    <Space
                      direction="vertical"
                      size={6}
                      style={{ width: '100%', alignItems: 'flex-start' }}
                    >
                      <Text
                        style={{
                          color: active ? token.colorWhite : token.colorText,
                          wordBreak: 'break-all',
                          textAlign: 'left',
                        }}
                      >
                        {candidate.path}
                      </Text>
                      <Space size={[6, 6]} wrap>
                        <Tag color={active ? 'default' : 'blue'}>
                          {t('remote.config.candidateRuns', { count: candidate.runCount })}
                        </Tag>
                        {candidate.hasArchive && (
                          <Tag color={active ? 'default' : 'green'}>
                            {t('remote.config.candidateArchive')}
                          </Tag>
                        )}
                        {candidate.hasIndex && (
                          <Tag color={active ? 'default' : 'purple'}>
                            {t('remote.config.candidateIndex')}
                          </Tag>
                        )}
                      </Space>
                    </Space>
                  </Button>
                )
              })
            ) : storageCandidatesRequested ? (
              <Text type="secondary">{t('remote.config.noDetectedStorageRoots')}</Text>
            ) : (
              <Text type="secondary">{t('remote.config.detectPrompt')}</Text>
            )}
          </Space>
        </Form.Item>

        <Divider style={{ margin: '8px 0 16px' }} />

        <Form.Item
          label={t('remote.config.confirmStorageRoot')}
          name="remoteRoot"
          rules={[{ required: true, message: t('remote.form.required') }]}
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

        <Form.Item
          label={t('remote.form.remotePort')}
          name="remotePort"
        >
          <Input type="number" placeholder="23300" />
        </Form.Item>
      </Form>

      {/* Action Buttons */}
      <Space style={{ marginTop: 16 }}>
        <Button
          type="primary"
          icon={<SaveOutlined />}
          onClick={handleConfirm}
          loading={loading}
          size="large"
        >
          {t('remote.form.saveConfig')}
        </Button>
        <Button onClick={onCancel} disabled={loading}>
          {t('remote.form.cancel')}
        </Button>
      </Space>
    </Card>
  )
}
