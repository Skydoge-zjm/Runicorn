import React, { useState, useEffect, useCallback } from 'react'
import { Modal, Table, Button, Space, Tag, message, Tooltip, Alert, Typography, Popconfirm } from 'antd'
import { DeleteOutlined, UndoOutlined, ClearOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { listDeletedRuns, restoreRuns, emptyRecycleBin } from '../api'
import { useTranslation } from 'react-i18next'
import logger from '../utils/logger'

interface DeletedRun {
  id: string
  project: string
  name: string
  created_time: number
  deleted_at: number
  delete_reason: string
  original_status: string
  run_dir: string
}

interface RecycleBinProps {
  open: boolean
  onClose: () => void
  onRestore?: () => void
}

export default function RecycleBin({ open, onClose, onRestore }: RecycleBinProps) {
  const { t } = useTranslation()
  const [deletedRuns, setDeletedRuns] = useState<DeletedRun[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([])
  const [restoreLoading, setRestoreLoading] = useState(false)
  const [emptyLoading, setEmptyLoading] = useState(false)

  const fetchDeletedRuns = useCallback(async () => {
    if (!open) return
    
    setLoading(true)
    try {
      const result = await listDeletedRuns()
      setDeletedRuns(result.deleted_runs || [])
    } catch (error) {
      logger.error('Failed to fetch deleted runs:', error)
      message.error(t('recycle_bin.fetch_failed') || 'Failed to load recycle bin')
    } finally {
      setLoading(false)
    }
  }, [open, t])

  useEffect(() => {
    if (open) {
      fetchDeletedRuns()
      setSelectedRowKeys([]) // Clear selection when opening
    }
  }, [open, fetchDeletedRuns])

  const handleRestore = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('recycle_bin.select_to_restore') || 'Please select runs to restore')
      return
    }

    setRestoreLoading(true)
    try {
      const result = await restoreRuns(selectedRowKeys)
      
      if (result.restored_count > 0) {
        message.success(t('recycle_bin.restore_success', { count: result.restored_count }) || `Restored ${result.restored_count} runs`)
        setSelectedRowKeys([])
        fetchDeletedRuns() // Refresh deleted runs list
        onRestore?.() // Notify parent to refresh main list
      } else {
        message.warning('No runs were restored')
      }
    } catch (error) {
      logger.error('Restore failed:', error)
      message.error(t('recycle_bin.restore_failed') || 'Failed to restore runs')
    } finally {
      setRestoreLoading(false)
    }
  }

  const handleEmptyBin = async () => {
    setEmptyLoading(true)
    try {
      const result = await emptyRecycleBin()
      message.success(t('recycle_bin.empty_success', { count: result.permanently_deleted }) || `Permanently deleted ${result.permanently_deleted} runs`)
      fetchDeletedRuns()
    } catch (error) {
      logger.error('Empty bin failed:', error)
      message.error(t('recycle_bin.empty_failed') || 'Failed to empty recycle bin')
    } finally {
      setEmptyLoading(false)
    }
  }

  const columns = [
    {
      title: t('table.run_id'),
      dataIndex: 'id',
      key: 'id',
      render: (id: string) => (
        <Typography.Text code style={{ fontSize: '12px' }}>
          {id}
        </Typography.Text>
      )
    },
    {
      title: t('table.project'),
      dataIndex: 'project',
      key: 'project',
      render: (project: string) => (
        <Tag color="blue">{project}</Tag>
      )
    },
    {
      title: t('table.name'),
      dataIndex: 'name', 
      key: 'name',
      render: (name: string) => (
        <Tag color="purple">{name}</Tag>
      )
    },
    {
      title: t('recycle_bin.original_status'),
      dataIndex: 'original_status',
      key: 'original_status',
      render: (status: string) => (
        <Tag color={
          status === 'running' ? 'processing' :
          status === 'finished' ? 'success' :
          status === 'failed' ? 'error' : 'default'
        }>
          {status}
        </Tag>
      )
    },
    {
      title: t('recycle_bin.deleted_at'),
      dataIndex: 'deleted_at',
      key: 'deleted_at',
      render: (timestamp: number) => (
        <Tooltip title={new Date(timestamp * 1000).toLocaleString()}>
          {new Date(timestamp * 1000).toLocaleDateString()}
        </Tooltip>
      )
    },
    {
      title: t('table.actions'),
      key: 'actions',
      render: (_: any, record: DeletedRun) => (
        <Space size="small">
          <Tooltip title={t('recycle_bin.restore_single')}>
            <Button 
              type="text"
              size="small"
              icon={<UndoOutlined />}
              onClick={async () => {
                setSelectedRowKeys([record.id])
                await handleRestore()
              }}
            />
          </Tooltip>
        </Space>
      )
    }
  ]

  return (
    <Modal
      title={
        <Space>
          <DeleteOutlined />
          <span>{t('recycle_bin.title') || 'Recycle Bin'}</span>
          <Tag color="orange">{deletedRuns.length}</Tag>
        </Space>
      }
      open={open}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="close" onClick={onClose}>
          {t('experiments.cancel') || 'Close'}
        </Button>,
        <Button 
          key="restore" 
          type="primary"
          icon={<UndoOutlined />}
          loading={restoreLoading}
          disabled={selectedRowKeys.length === 0}
          onClick={handleRestore}
        >
          {t('recycle_bin.restore_selected') || 'Restore Selected'} 
          {selectedRowKeys.length > 0 && ` (${selectedRowKeys.length})`}
        </Button>,
        <Popconfirm
          key="empty"
          title={t('recycle_bin.empty_confirm_title') || 'Empty Recycle Bin'}
          description={t('recycle_bin.empty_confirm_desc') || 'This will permanently delete all runs in recycle bin. This cannot be undone!'}
          okText={t('recycle_bin.empty_confirm') || 'Yes, Delete All'}
          okType="danger"
          cancelText={t('experiments.cancel') || 'Cancel'}
          onConfirm={handleEmptyBin}
        >
          <Button 
            danger
            icon={<ClearOutlined />}
            loading={emptyLoading}
            disabled={deletedRuns.length === 0}
          >
            {t('recycle_bin.empty_bin') || 'Empty Bin'}
          </Button>
        </Popconfirm>
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message={t('recycle_bin.description') || 'Recycle Bin contains soft-deleted experiments. Files are preserved and can be restored.'}
          type="info"
          icon={<InfoCircleOutlined />}
          showIcon
        />
        
        <Table
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as string[]),
            getCheckboxProps: (record) => ({
              disabled: false
            }),
          }}
          dataSource={deletedRuns}
          columns={columns}
          loading={loading}
          rowKey="id"
          size="small"
          pagination={{
            pageSize: 10,
            showSizeChanger: false,
            showQuickJumper: false,
            showTotal: (total, range) => 
              t('recycle_bin.table_total', { from: range[0], to: range[1], total }) || 
              `${range[0]}-${range[1]} of ${total} items`
          }}
          locale={{
            emptyText: (
              <div style={{ padding: 20, textAlign: 'center' }}>
                <Typography.Text type="secondary">
                  {t('recycle_bin.empty_state') || 'Recycle bin is empty'}
                </Typography.Text>
              </div>
            )
          }}
        />
        
        {selectedRowKeys.length > 0 && (
          <Alert
            message={t('recycle_bin.selection_info', { count: selectedRowKeys.length }) || `${selectedRowKeys.length} runs selected for restoration`}
            type="info"
            style={{ marginTop: 8 }}
          />
        )}
      </Space>
    </Modal>
  )
}
