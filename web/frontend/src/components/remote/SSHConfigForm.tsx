import React from 'react'
import { Form, Input, InputNumber, Radio, Upload, Button, Space, Tag } from 'antd'
import { KeyOutlined, LockOutlined, FolderOpenOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

const { TextArea } = Input

export interface SSHConfig {
  host: string
  port: number
  username: string
  authMethod: 'key' | 'password' | 'agent'
  password?: string
  privateKey?: string
  privateKeyPath?: string
  passphrase?: string
}

interface SSHConfigFormProps {
  config: SSHConfig
  onChange: (config: SSHConfig) => void
  disabled?: boolean
}

export default function SSHConfigForm({ config, onChange, disabled }: SSHConfigFormProps) {
  const { t } = useTranslation()
  
  const handleKeyFileUpload = (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      onChange({ ...config, privateKey: content })
    }
    reader.readAsText(file)
    return false  // Prevent auto upload
  }
  
  return (
    <Form layout="vertical">
      <Form.Item 
        label={t('remote_storage.form.host')} 
        required
        help={t('remote_storage.form.host_help')}
      >
        <Input
          value={config.host}
          onChange={(e) => onChange({ ...config, host: e.target.value })}
          placeholder={t('remote_storage.form.host_placeholder')}
          disabled={disabled}
        />
      </Form.Item>
      
      <Space style={{ width: '100%' }}>
        <Form.Item label={t('remote_storage.form.port')} style={{ flex: 1 }}>
          <InputNumber
            value={config.port}
            onChange={(port) => onChange({ ...config, port: port || 22 })}
            min={1}
            max={65535}
            style={{ width: '100%' }}
            disabled={disabled}
          />
        </Form.Item>
        
        <Form.Item label={t('remote_storage.form.username')} required style={{ flex: 2 }}>
          <Input
            value={config.username}
            onChange={(e) => onChange({ ...config, username: e.target.value })}
            placeholder={t('remote_storage.form.username_placeholder')}
            disabled={disabled}
          />
        </Form.Item>
      </Space>
      
      <Form.Item label={t('remote_storage.form.auth_method')}>
        <Radio.Group 
          value={config.authMethod}
          onChange={(e) => onChange({ ...config, authMethod: e.target.value })}
          disabled={disabled}
        >
          <Radio value="key"><KeyOutlined /> {t('remote_storage.form.auth_key')}</Radio>
          <Radio value="password"><LockOutlined /> {t('remote_storage.form.auth_password')}</Radio>
          <Radio value="agent">{t('remote_storage.form.auth_agent')}</Radio>
        </Radio.Group>
      </Form.Item>
      
      {config.authMethod === 'key' && (
        <>
          <Form.Item label={t('remote_storage.form.private_key')}>
            <TextArea
              rows={6}
              value={config.privateKey || ''}
              onChange={(e) => onChange({ ...config, privateKey: e.target.value })}
              placeholder={t('remote_storage.form.private_key_placeholder')}
              style={{ fontFamily: 'monospace', fontSize: 12 }}
              disabled={disabled}
            />
            <Space style={{ marginTop: 8 }}>
              <Upload
                beforeUpload={handleKeyFileUpload}
                showUploadList={false}
                accept=".pem,.key,*"
                disabled={disabled}
              >
                <Button icon={<FolderOpenOutlined />} disabled={disabled}>
                  {t('remote_storage.form.select_key_file')}
                </Button>
              </Upload>
              {config.privateKey && (
                <Tag color="success">{t('remote_storage.form.key_loaded')}</Tag>
              )}
            </Space>
          </Form.Item>
          
          <Form.Item label={t('remote_storage.form.private_key_passphrase')}>
            <Input.Password
              value={config.passphrase || ''}
              onChange={(e) => onChange({ ...config, passphrase: e.target.value })}
              placeholder={t('remote_storage.form.private_key_passphrase_placeholder')}
              disabled={disabled}
            />
          </Form.Item>
        </>
      )}
      
      {config.authMethod === 'password' && (
        <Form.Item label={t('remote_storage.form.password')}>
          <Input.Password
            value={config.password || ''}
            onChange={(e) => onChange({ ...config, password: e.target.value })}
            placeholder={t('remote_storage.form.password_placeholder')}
            disabled={disabled}
          />
        </Form.Item>
      )}
    </Form>
  )
}
