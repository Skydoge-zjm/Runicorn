import React, { useEffect, useState } from 'react'
import { Modal, Progress, Typography, Space, Button, message, Alert, Descriptions, Badge } from 'antd'
import { 
  DownloadOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined,
  StopOutlined,
  FolderOpenOutlined
} from '@ant-design/icons'
import { getDownloadStatus, cancelDownload } from '../api'
import { useTranslation } from 'react-i18next'

const { Text } = Typography

interface DownloadProgressModalProps {
  visible: boolean
  taskId: string | null
  artifactName: string
  artifactVersion: number
  onClose: () => void
  onComplete?: (targetDir: string) => void
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

export default function DownloadProgressModal({
  visible,
  taskId,
  artifactName,
  artifactVersion,
  onClose,
  onComplete
}: DownloadProgressModalProps) {
  const { t } = useTranslation()
  const [task, setTask] = useState<any>(null)
  const [cancelling, setCancelling] = useState(false)
  
  // Poll download status
  useEffect(() => {
    if (!visible || !taskId) {
      setTask(null)
      return
    }
    
    const poll = async () => {
      try {
        const status = await getDownloadStatus(taskId)
        setTask(status)
        
          // Check if completed
        if (status.status === 'completed') {
          message.success(t('remote_storage.download.complete'))
          if (onComplete) {
            onComplete(status.target_dir)
          }
          // Don't auto-close, let user see the result
        }
        
        // Check if failed
        if (status.status === 'failed') {
          message.error(`${t('remote_storage.download.failed')}: ${status.error || ''}`)
        }
      } catch (error: any) {
        message.error(`${t('remote_storage.download.failed')}: ${error.message}`)
      }
    }
    
    poll()
    const interval = setInterval(poll, 1000)  // Poll every second
    
    return () => clearInterval(interval)
  }, [visible, taskId, onComplete])
  
  // Handle cancel
  const handleCancel = async () => {
    if (!taskId) return
    
    setCancelling(true)
    try {
      await cancelDownload(taskId)
      message.info(t('remote_storage.download.cancel_button'))
      onClose()
    } catch (error: any) {
      message.error(`${t('remote_storage.download.failed')}: ${error.message}`)
    } finally {
      setCancelling(false)
    }
  }
  
  // Handle close
  const handleClose = () => {
    if (task?.status === 'running') {
      Modal.confirm({
        title: t('remote_storage.download.confirm_close'),
        content: t('remote_storage.download.confirm_close_desc'),
        onOk: onClose
      })
    } else {
      onClose()
    }
  }
  
  // Handle open folder
  const handleOpenFolder = () => {
    if (task?.target_dir) {
      message.info(t('remote_storage.download.location_info', { path: task.target_dir }))
      // Note: In Tauri desktop app, can use shell.open()
      // For web, just show the path
    }
  }
  
  if (!task) {
    return null
  }
  
  const isRunning = task.status === 'running'
  const isCompleted = task.status === 'completed'
  const isFailed = task.status === 'failed'
  
  return (
    <Modal
      title={
        <Space>
          <DownloadOutlined />
          <span>{t('remote_storage.download.modal_title', { name: artifactName, version: artifactVersion })}</span>
        </Space>
      }
      open={visible}
      onCancel={handleClose}
      footer={
        <Space>
          {isRunning && (
            <Button 
              icon={<StopOutlined />}
              danger
              onClick={handleCancel}
              loading={cancelling}
            >
              {t('remote_storage.download.cancel_button')}
            </Button>
          )}
          {isCompleted && (
            <Button 
              icon={<FolderOpenOutlined />}
              onClick={handleOpenFolder}
            >
              {t('remote_storage.download.view_location')}
            </Button>
          )}
          <Button onClick={handleClose}>
            {isRunning ? t('remote_storage.download.minimize') : t('remote_storage.download.close')}
          </Button>
        </Space>
      }
      width={600}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Status */}
        {isRunning && (
          <Alert
            message={t('remote_storage.download.downloading')}
            type="info"
            showIcon
          />
        )}
        {isCompleted && (
          <Alert
            message={t('remote_storage.download.complete')}
            description={t('remote_storage.download.complete_desc', { path: task.target_dir })}
            type="success"
            icon={<CheckCircleOutlined />}
            showIcon
          />
        )}
        {isFailed && (
          <Alert
            message={t('remote_storage.download.failed')}
            description={task.error || ''}
            type="error"
            icon={<CloseCircleOutlined />}
            showIcon
          />
        )}
        
        {/* Progress Bar */}
        <div>
          <Progress
            percent={Math.round(task.progress_percent || 0)}
            status={
              isCompleted ? 'success' :
              isFailed ? 'exception' :
              'active'
            }
            format={(percent) => `${percent}%`}
          />
          <Space direction="vertical" size="small" style={{ width: '100%', marginTop: 12 }}>
            <Text type="secondary">
              {t('remote_storage.download.files')}: {task.downloaded_files} / {task.total_files}
            </Text>
            <Text type="secondary">
              {t('remote_storage.download.size')}: {formatBytes(task.downloaded_bytes)} / {formatBytes(task.total_bytes)}
            </Text>
            {isRunning && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {t('remote_storage.download.estimated_remaining')}: {formatBytes((task.total_bytes - task.downloaded_bytes))}
              </Text>
            )}
          </Space>
        </div>
        
        {/* Details */}
        <Descriptions size="small" column={2} bordered>
          <Descriptions.Item label={t('remote_storage.download.artifact')}>{task.artifact_name}</Descriptions.Item>
          <Descriptions.Item label={t('remote_storage.download.version')}>v{task.artifact_version}</Descriptions.Item>
          <Descriptions.Item label={t('remote_storage.download.type')}>{task.artifact_type}</Descriptions.Item>
          <Descriptions.Item label={t('remote_storage.download.status')}>
            {isRunning && <Badge status="processing" text={t('remote_storage.download.status_running')} />}
            {isCompleted && <Badge status="success" text={t('remote_storage.download.status_completed')} />}
            {isFailed && <Badge status="error" text={t('remote_storage.download.status_failed')} />}
          </Descriptions.Item>
          {isCompleted && (
            <Descriptions.Item label={t('remote_storage.download.save_location')} span={2}>
              <Text code copyable style={{ fontSize: 11 }}>
                {task.target_dir}
              </Text>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Space>
    </Modal>
  )
}

