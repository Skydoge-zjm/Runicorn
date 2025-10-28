/**
 * SSH Connection Form Component
 * 
 * Form for configuring SSH connection and Remote Viewer settings
 */

import React, { useState } from 'react'
import {
  Form,
  Input,
  InputNumber,
  Radio,
  Button,
  Space,
  Divider,
  Checkbox,
  Row,
  Col,
  message
} from 'antd'
import { FolderOpenOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { SSHConnectionConfig } from '../../types/remote'

interface SSHConnectionFormProps {
  onSubmit: (config: SSHConnectionConfig) => Promise<void>
  onTest?: (config: SSHConnectionConfig) => Promise<void>
  onCancel?: () => void
  loading?: boolean
  initialValues?: Partial<SSHConnectionConfig>
}

export default function SSHConnectionForm({
  onSubmit,
  onTest,
  onCancel,
  loading = false,
  initialValues
}: SSHConnectionFormProps) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [authMethod, setAuthMethod] = useState<'password' | 'key'>(
    initialValues?.authMethod || 'password'
  )
  const [saveConfig, setSaveConfig] = useState(false)

  const handleSubmit = async (values: any) => {
    console.log('Form values:', {
      ...values,
      password: values.password ? '***' : undefined,
      savePassword: values.savePassword
    })
    
    const config: SSHConnectionConfig = {
      host: values.host,
      port: values.port || 22,
      username: values.username,
      authMethod: values.authMethod,
      password: values.password,
      privateKeyPath: values.privateKeyPath,
      passphrase: values.passphrase,
      remoteRoot: values.remoteRoot,
      localPort: values.localPort,
      remotePort: values.remotePort || 23300,
      saveName: values.saveName,
      savePassword: values.savePassword || false  // 必须传递这个字段！
    }
    
    console.log('Config to submit:', {
      ...config,
      password: config.password ? '***' : undefined
    })

    try {
      await onSubmit(config)
      message.success(t('remote.message.connectSuccess'))
      form.resetFields()
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('remote.message.connectFailed'))
    }
  }

  const handleTest = async () => {
    try {
      const values = await form.validateFields()
      const config: SSHConnectionConfig = {
        host: values.host,
        port: values.port || 22,
        username: values.username,
        authMethod: values.authMethod,
        password: values.password,
        privateKeyPath: values.privateKeyPath,
        passphrase: values.passphrase,
        remoteRoot: values.remoteRoot,
        localPort: values.localPort,
        remotePort: values.remotePort || 23300
      }
      
      if (onTest) {
        await onTest(config)
        message.success(t('remote.message.testSuccess'))
      }
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message)
      }
    }
  }

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={{
        port: 22,
        remotePort: 23300,
        authMethod: 'password',
        ...initialValues
      }}
      onFinish={handleSubmit}
    >
      {/* SSH Connection Info */}
      <Form.Item
        label={t('remote.form.host')}
        name="host"
        rules={[{ required: true, message: 'Please enter host address' }]}
      >
        <Input placeholder={t('remote.form.hostPlaceholder')} />
      </Form.Item>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label={t('remote.form.port')}
            name="port"
          >
            <InputNumber min={1} max={65535} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label={t('remote.form.username')}
            name="username"
            rules={[{ required: true, message: 'Please enter username' }]}
          >
            <Input placeholder={t('remote.form.usernamePlaceholder')} />
          </Form.Item>
        </Col>
      </Row>

      {/* Authentication Method */}
      <Form.Item
        label={t('remote.form.authMethod')}
        name="authMethod"
      >
        <Radio.Group onChange={e => setAuthMethod(e.target.value)}>
          <Radio value="password">{t('remote.form.passwordAuth')}</Radio>
          <Radio value="key">{t('remote.form.keyAuth')}</Radio>
        </Radio.Group>
      </Form.Item>

      {/* Password or Private Key */}
      {authMethod === 'password' ? (
        <Form.Item
          label={t('remote.form.password')}
          name="password"
          rules={[{ required: true, message: 'Please enter password' }]}
        >
          <Input.Password />
        </Form.Item>
      ) : (
        <>
          <Form.Item
            label={t('remote.form.privateKey')}
            name="privateKeyPath"
            rules={[{ required: true, message: 'Please enter private key path' }]}
          >
            <Input placeholder={t('remote.form.privateKeyPlaceholder')} />
          </Form.Item>
          <Form.Item
            label={t('remote.form.passphrase')}
            name="passphrase"
          >
            <Input.Password />
          </Form.Item>
        </>
      )}


      {/* Save Configuration */}
      <Form.Item>
        <Space direction="vertical">
          <Checkbox checked={saveConfig} onChange={e => setSaveConfig(e.target.checked)}>
            {t('remote.form.saveConfig')}
          </Checkbox>
          {saveConfig && authMethod === 'password' && (
            <Form.Item name="savePassword" valuePropName="checked" initialValue={false} noStyle>
              <Checkbox style={{ marginLeft: 24 }}>
                {t('remote.form.savePassword')}
              </Checkbox>
            </Form.Item>
          )}
        </Space>
      </Form.Item>

      {saveConfig && (
        <Form.Item
          label={t('remote.form.saveName')}
          name="saveName"
        >
          <Input placeholder={t('remote.form.saveNamePlaceholder')} />
        </Form.Item>
      )}

      {/* Action Buttons */}
      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={loading} size="large">
            {t('remote.form.connectButton')}
          </Button>
          {onTest && (
            <Button onClick={handleTest}>
              {t('remote.form.testConnection')}
            </Button>
          )}
          {onCancel && (
            <Button onClick={onCancel}>
              {t('remote.form.cancel')}
            </Button>
          )}
        </Space>
      </Form.Item>
    </Form>
  )
}
