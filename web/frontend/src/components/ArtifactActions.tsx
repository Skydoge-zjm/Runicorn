import React, { useState, useEffect } from 'react'
import { Space, Button, message, Modal } from 'antd'
import { 
  DownloadOutlined, 
  DeleteOutlined, 
  FolderOpenOutlined,
  TagOutlined,
  StarOutlined
} from '@ant-design/icons'
import {
  deleteArtifactVersion,
  remoteDownloadArtifact,
  getStorageMode
} from '../api'
import DownloadProgressModal from './DownloadProgressModal'
import { useTranslation } from 'react-i18next'

interface ArtifactActionsProps {
  name: string
  type: string
  version: number
  size_bytes: number
  onDeleted?: () => void
  onDownloaded?: (targetDir: string) => void
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

export default function ArtifactActions({
  name,
  type,
  version,
  size_bytes,
  onDeleted,
  onDownloaded
}: ArtifactActionsProps) {
  const { t } = useTranslation()
  const [isRemote, setIsRemote] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [downloadTaskId, setDownloadTaskId] = useState<string | null>(null)
  const [downloadModalVisible, setDownloadModalVisible] = useState(false)
  const [deleting, setDeleting] = useState(false)
  
  // Check storage mode
  useEffect(() => {
    const checkMode = async () => {
      try {
        const mode = await getStorageMode()
        setIsRemote(mode.mode === 'remote' && mode.remote_connected)
      } catch (error) {
        setIsRemote(false)
      }
    }
    
    checkMode()
    const interval = setInterval(checkMode, 5000)
    
    return () => clearInterval(interval)
  }, [])
  
  // Handle download
  const handleDownload = async () => {
    if (!isRemote) {
      message.info(t('remote_storage.actions.local_no_download'))
      return
    }
    
    setDownloading(true)
    
    try {
      const result = await remoteDownloadArtifact(name, version, type)
      
      if (result.ok && result.task_id) {
        setDownloadTaskId(result.task_id)
        setDownloadModalVisible(true)
        message.success(t('remote_storage.msg.sync_started'))
      }
    } catch (error: any) {
      message.error(`${t('remote_storage.download.failed')}: ${error.message}`)
    } finally {
      setDownloading(false)
    }
  }
  
  // Handle download complete
  const handleDownloadComplete = (targetDir: string) => {
    message.success(t('remote_storage.download.complete_desc', { path: targetDir }))
    if (onDownloaded) {
      onDownloaded(targetDir)
    }
  }
  
  // Handle delete
  const handleDelete = () => {
    Modal.confirm({
      title: t('remote_storage.actions.delete_confirm', {
        name,
        version,
        remote: isRemote ? t('remote_storage.actions.delete_remote_note') : ''
      }),
      okText: t('remote_storage.actions.delete'),
      okType: 'danger',
      cancelText: t('remote_storage.actions.cancel'),
      onOk: async () => {
        setDeleting(true)
        try {
          const result = await deleteArtifactVersion(name, version, type, false)
          if (result.success) {
            message.success(t('remote_storage.actions.delete_success', { message: result.message }))
            if (onDeleted) {
              onDeleted()
            }
          }
        } catch (error: any) {
          message.error(`${t('remote_storage.actions.delete_failed')}: ${error.message}`)
        } finally {
          setDeleting(false)
        }
      }
    })
  }
  
  return (
    <>
      <Space>
        {isRemote ? (
          <>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              loading={downloading}
              onClick={handleDownload}
              size="large"
            >
              {t('remote_storage.actions.download_local', { size: formatBytes(size_bytes) })}
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              loading={deleting}
              onClick={handleDelete}
            >
              {t('remote_storage.actions.delete_version')}
            </Button>
          </>
        ) : (
          <>
            <Button
              icon={<FolderOpenOutlined />}
              onClick={() => message.info(t('remote_storage.actions.feature_dev'))}
            >
              {t('remote_storage.actions.open_folder')}
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              loading={deleting}
              onClick={handleDelete}
            >
              {t('remote_storage.actions.delete_version')}
            </Button>
          </>
        )}
        
        <Button icon={<TagOutlined />} onClick={() => message.info(t('remote_storage.actions.feature_dev'))}>
          {t('remote_storage.actions.manage_tags')}
        </Button>
        <Button icon={<StarOutlined />} onClick={() => message.info(t('remote_storage.actions.feature_dev'))}>
          {t('remote_storage.actions.set_alias')}
        </Button>
      </Space>
      
      {/* Download Progress Modal */}
      <DownloadProgressModal
        visible={downloadModalVisible}
        taskId={downloadTaskId}
        artifactName={name}
        artifactVersion={version}
        onClose={() => setDownloadModalVisible(false)}
        onComplete={handleDownloadComplete}
      />
    </>
  )
}

