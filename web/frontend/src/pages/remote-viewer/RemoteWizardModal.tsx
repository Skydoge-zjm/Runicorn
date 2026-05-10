import { Alert, Button, Checkbox, Col, Divider, Form, Input, InputNumber, Modal, Radio, Row, Space, Spin, Typography, theme } from 'antd'
import type { FormInstance } from 'antd'
import { useTranslation } from 'react-i18next'

import CondaEnvSelector from '../../components/remote/CondaEnvSelector'
import RemoteConfigCard from '../../components/remote/RemoteConfigCard'
import type { RemoteStorageCandidate, SSHConnectionState, SavedConnectionProfile, SavedServer } from '../../types/remote'

const { Text } = Typography

type Props = {
  connecting: boolean
  fetchingConfig: boolean
  fetchingEnvs: boolean
  fetchingStorageCandidates: boolean
  loading: boolean
  open: boolean
  profile: SavedConnectionProfile | null
  progressText: string | null
  server: SavedServer | null
  serverForm: FormInstance
  sshConnection: SSHConnectionState | null
  storageCandidates: RemoteStorageCandidate[]
  storageCandidatesRequested: boolean
  title: string
  onCancel: () => void
  onCloseForm: () => void
  onConfirmConfig: (profileName: string, remoteRoot: string, localPort?: number, remotePort?: number) => void
  onConnect: () => void
  onDetectStorageCandidates: (scanRoot: string, maxDepth: number) => void
  onSelectEnvironment: (envName: string) => void
}

export default function RemoteWizardModal({
  connecting,
  fetchingConfig,
  fetchingEnvs,
  fetchingStorageCandidates,
  loading,
  open,
  profile,
  progressText,
  server,
  serverForm,
  sshConnection,
  storageCandidates,
  storageCandidatesRequested,
  title,
  onCancel,
  onCloseForm,
  onConfirmConfig,
  onConnect,
  onDetectStorageCandidates,
  onSelectEnvironment,
}: Props) {
  const { t } = useTranslation()
  const { token } = theme.useToken()

  const isEnvironmentStep = Boolean(sshConnection && !sshConnection.remoteConfig)
  const step = !sshConnection ? 0 : sshConnection.remoteConfig ? 2 : 1
  const steps = [
    t('remote.wizard.step_connect'),
    t('remote.wizard.step_environment'),
    t('remote.wizard.step_config'),
  ]

  return (
    <Modal
      title={title}
      open={open}
      onCancel={onCancel}
      width={720}
      footer={null}
      destroyOnClose
      centered
      styles={{ body: { display: 'flex', flexDirection: 'column', padding: '16px 24px 12px' } }}
    >
      <div
        style={
          isEnvironmentStep
            ? {
                flex: 1,
                height: 'calc(80vh - 180px)',
                minHeight: 420,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
              }
            : {
                flex: 1,
                minHeight: 420,
                maxHeight: 'calc(80vh - 180px)',
                overflowY: 'auto',
                overflowX: 'hidden',
              }
        }
      >
        {!sshConnection ? (
          progressText ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 320, gap: 24 }}>
              <Spin size="large" />
              <Text style={{ fontSize: 16, color: token.colorTextSecondary }}>{progressText}</Text>
            </div>
          ) : (
            <>
              {server ? (
                <Alert
                  type="info"
                  showIcon
                  message={`${server.username}@${server.host}:${server.port}`}
                  style={{ marginBottom: 16 }}
                />
              ) : null}
              <Form
                form={serverForm}
                layout="vertical"
                initialValues={{
                  port: 22,
                  authMethod: server?.authMethod || 'password',
                  host: server?.host,
                  username: server?.username,
                  name: server?.name,
                  privateKeyPath: server?.privateKeyPath,
                  passphrase: server?.passphrase,
                  savePassword: server?.hasSavedPassword ?? false,
                  savePassphrase: server?.hasSavedPassphrase ?? false,
                }}
              >
                {!server && (
                  <Form.Item label={t('remote.form.saveName')} name="name">
                    <Input placeholder={t('remote.form.saveNamePlaceholder')} />
                  </Form.Item>
                )}

                {!server && (
                  <>
                    <Form.Item
                      label={t('remote.form.host')}
                      name="host"
                      rules={[{ required: true, message: t('remote.form.required') }]}
                    >
                      <Input placeholder={t('remote.form.hostPlaceholder')} />
                    </Form.Item>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item label={t('remote.form.port')} name="port">
                          <InputNumber min={1} max={65535} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          label={t('remote.form.username')}
                          name="username"
                          rules={[{ required: true, message: t('remote.form.required') }]}
                        >
                          <Input placeholder={t('remote.form.usernamePlaceholder')} />
                        </Form.Item>
                      </Col>
                    </Row>
                  </>
                )}

                <Form.Item label={t('remote.form.authMethod')} name="authMethod">
                  <Radio.Group>
                    <Radio value="password">{t('remote.form.passwordAuth')}</Radio>
                    <Radio value="key">{t('remote.form.keyAuth')}</Radio>
                  </Radio.Group>
                </Form.Item>

                <Form.Item noStyle shouldUpdate>
                  {() => {
                    const method = serverForm.getFieldValue('authMethod') as 'password' | 'key'
                    return method === 'password' ? (
                      <>
                        <Form.Item
                          label={t('remote.form.password')}
                          name="password"
                          rules={server?.authMethod === 'password' && (server.password || server.hasSavedPassword)
                            ? []
                            : [{ required: true, message: t('remote.form.required') }]}
                        >
                          <Input.Password />
                        </Form.Item>

                        <Form.Item name="savePassword" valuePropName="checked">
                          <Checkbox>{t('remote.form.savePassword')}</Checkbox>
                        </Form.Item>
                      </>
                    ) : (
                      <>
                        <Form.Item
                          label={t('remote.form.privateKey')}
                          name="privateKeyPath"
                          rules={[{ required: true, message: t('remote.form.required') }]}
                        >
                          <Input placeholder={t('remote.form.privateKeyPlaceholder')} />
                        </Form.Item>
                        <Form.Item label={t('remote.form.passphrase')} name="passphrase">
                          <Input.Password />
                        </Form.Item>
                        <Form.Item name="savePassphrase" valuePropName="checked">
                          <Checkbox>{t('remote.form.savePassphrase')}</Checkbox>
                        </Form.Item>
                      </>
                    )
                  }}
                </Form.Item>

                <Divider />
                <Space>
                  <Button type="primary" loading={connecting} onClick={onConnect}>
                    {t('remote.form.connectButton')}
                  </Button>
                  <Button onClick={onCloseForm}>
                    {t('remote.form.cancel')}
                  </Button>
                </Space>
              </Form>
            </>
          )
        ) : sshConnection.remoteConfig ? (
          <Spin spinning={fetchingConfig} tip={t('remote.config.fetchingConfig')}>
            <RemoteConfigCard
              config={sshConnection.remoteConfig}
              sshConfig={{
                ...sshConnection.config,
                saveName: profile?.name,
                remoteRoot: profile?.remoteRoot,
                localPort: profile?.localPort,
                remotePort: profile?.remotePort,
              }}
              onConfirm={onConfirmConfig}
              onCancel={onCancel}
              onDetectStorageCandidates={onDetectStorageCandidates}
              storageCandidates={storageCandidates}
              storageCandidatesLoading={fetchingStorageCandidates}
              storageCandidatesRequested={storageCandidatesRequested}
              loading={loading}
            />
          </Spin>
        ) : (
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <CondaEnvSelector
              envs={sshConnection.condaEnvs || []}
              connectionId={sshConnection.connectionId}
              initialEnv={profile?.condaEnv}
              onSelect={onSelectEnvironment}
              onCancel={onCancel}
              loading={fetchingConfig || fetchingEnvs}
            />
          </div>
        )}
      </div>

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 6,
          paddingTop: 16,
          borderTop: `1px solid ${token.colorBorderSecondary}`,
          marginTop: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {steps.map((_, index) => (
            <div key={index} style={{ display: 'flex', alignItems: 'center' }}>
              {index > 0 && (
                <div
                  style={{
                    width: 48,
                    height: 2,
                    background: index <= step ? token.colorPrimary : token.colorBorderSecondary,
                    transition: 'background 0.3s',
                  }}
                />
              )}
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  flexShrink: 0,
                  background: index <= step ? token.colorPrimary : 'transparent',
                  border: `2px solid ${index <= step ? token.colorPrimary : token.colorBorderSecondary}`,
                  transition: 'all 0.3s',
                }}
              />
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {steps.map((label, index) => (
            <div key={index} style={{ display: 'flex', alignItems: 'center' }}>
              {index > 0 && <div style={{ width: 48 }} />}
              <span
                style={{
                  width: 28,
                  textAlign: 'center',
                  fontSize: 13,
                  color: index <= step ? token.colorPrimary : token.colorTextQuaternary,
                  transition: 'color 0.3s',
                  whiteSpace: 'nowrap',
                }}
              >
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Modal>
  )
}
