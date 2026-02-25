import { useState, useEffect, useCallback } from 'react'
import { Modal, Table, Button, Space, Tag, message, Tooltip, Alert, Typography, Popconfirm, Descriptions, Spin, theme } from 'antd'
import { DeleteOutlined, UndoOutlined, ClearOutlined, InfoCircleOutlined, ExclamationCircleOutlined, FileOutlined } from '@ant-design/icons'
import { listDeletedRuns, restoreRuns, permanentDeleteRunsBatch, getRunAssetRefs, type RunAssetRefs } from '../api'
import { useTranslation } from 'react-i18next'
import logger from '../utils/logger'

interface DeletedRun {
  id: string
  path: string
  alias: string | null
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
  const { token } = theme.useToken()
  const [deletedRuns, setDeletedRuns] = useState<DeletedRun[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([])
  const [restoreLoading, setRestoreLoading] = useState(false)
  const [emptyLoading, setEmptyLoading] = useState(false)
  const [permanentDeleteLoading, setPermanentDeleteLoading] = useState(false)
  
  // Asset preview state
  const [previewRunId, setPreviewRunId] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [assetRefs, setAssetRefs] = useState<RunAssetRefs | null>(null)

  const fetchDeletedRuns = useCallback(async () => {
    if (!open) return
    
    setLoading(true)
    try {
      const result = await listDeletedRuns()
      setDeletedRuns(result.deleted_runs || [])
    } catch (error) {
      logger.error('Failed to fetch deleted runs:', error)
      message.error(t('recycle_bin.fetch_failed'))
    } finally {
      setLoading(false)
    }
  }, [open, t])

  useEffect(() => {
    if (open) {
      fetchDeletedRuns()
      setSelectedRowKeys([])
      setPreviewRunId(null)
      setAssetRefs(null)
    }
  }, [open, fetchDeletedRuns])

  // Fetch asset refs for preview
  const fetchAssetRefs = useCallback(async (runId: string) => {
    setPreviewLoading(true)
    setPreviewRunId(runId)
    try {
      const refs = await getRunAssetRefs(runId)
      setAssetRefs(refs)
    } catch (error) {
      logger.error('Failed to fetch asset refs:', error)
      // Don't show error - asset refs may not exist for old runs
      setAssetRefs(null)
    } finally {
      setPreviewLoading(false)
    }
  }, [])

  const handleRestore = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('recycle_bin.select_to_restore'))
      return
    }

    setRestoreLoading(true)
    try {
      const result = await restoreRuns(selectedRowKeys)

      // Check for conflict errors
      const conflictIds = Object.entries(result.results || {})
        .filter(([, r]: [string, any]) => r.error === 'conflict')
        .map(([id]: [string, any]) => id)

      if (result.restored_count > 0) {
        message.success(t('recycle_bin.restore_success', { count: result.restored_count }))
        setSelectedRowKeys([])
        fetchDeletedRuns()
        onRestore?.()
      }
      if (conflictIds.length > 0) {
        message.warning(t('recycle_bin.restore_conflict', { count: conflictIds.length }))
      } else if (result.restored_count === 0) {
        message.warning(t('recycle_bin.restore_failed'))
      }
    } catch (error) {
      logger.error('Restore failed:', error)
      message.error(t('recycle_bin.restore_failed'))
    } finally {
      setRestoreLoading(false)
    }
  }

  // Permanent delete with asset cleanup
  const handlePermanentDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('recycle_bin.select_to_delete'))
      return
    }

    setPermanentDeleteLoading(true)
    try {
      const result = await permanentDeleteRunsBatch(selectedRowKeys, false)
      
      if (result.deleted_count > 0) {
        message.success(
          t('recycle_bin.permanent_delete_success', { 
            count: result.deleted_count,
            blobs: result.total_blobs_deleted 
          })
        )
        setSelectedRowKeys([])
        setPreviewRunId(null)
        setAssetRefs(null)
        fetchDeletedRuns()
      } else {
        message.warning('No runs were deleted')
      }
    } catch (error) {
      logger.error('Permanent delete failed:', error)
      message.error(t('recycle_bin.permanent_delete_failed'))
    } finally {
      setPermanentDeleteLoading(false)
    }
  }

  const handleEmptyBin = async () => {
    setEmptyLoading(true)
    try {
      // Use permanent delete for all runs to clean up assets
      const allRunIds = deletedRuns.map(r => r.id)
      if (allRunIds.length === 0) {
        message.info(t('recycle_bin.already_empty'))
        setEmptyLoading(false)
        return
      }
      
      const result = await permanentDeleteRunsBatch(allRunIds, false)
      message.success(
        t('recycle_bin.empty_success', { count: result.deleted_count })
      )
      fetchDeletedRuns()
    } catch (error) {
      logger.error('Empty bin failed:', error)
      message.error(t('recycle_bin.empty_failed'))
    } finally {
      setEmptyLoading(false)
    }
  }

  const columns = [
    {
      title: t('table.run_id'),
      dataIndex: 'id',
      key: 'id',
      width: 200,
      render: (id: string) => (
        <Tooltip title={t('recycle_bin.click_to_preview')}>
          <Typography.Text 
            code 
            style={{ fontSize: '12px', cursor: 'pointer' }}
            onClick={() => fetchAssetRefs(id)}
          >
            {id}
          </Typography.Text>
        </Tooltip>
      )
    },
    {
      title: t('table.path'),
      dataIndex: 'path',
      key: 'path',
      width: 150,
      render: (path: string) => (
        <Tooltip title={path}>
          <code style={{ fontSize: '12px', color: token.colorPrimary }}>{path}</code>
        </Tooltip>
      )
    },
    {
      title: t('table.alias'),
      dataIndex: 'alias', 
      key: 'alias',
      width: 100,
      render: (alias: string | null) => alias ? (
        <Tag color="purple">{alias}</Tag>
      ) : (
        <span style={{ color: token.colorTextQuaternary }}>-</span>
      )
    },
    {
      title: t('recycle_bin.original_status'),
      dataIndex: 'original_status',
      key: 'original_status',
      width: 100,
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
      width: 120,
      render: (timestamp: number) => (
        <Tooltip title={new Date(timestamp * 1000).toLocaleString()}>
          {new Date(timestamp * 1000).toLocaleDateString()}
        </Tooltip>
      )
    },
    {
      title: t('table.actions'),
      key: 'actions',
      width: 100,
      render: (_: any, record: DeletedRun) => (
        <Space size="small">
          <Tooltip title={t('recycle_bin.restore_single')}>
            <Button 
              type="text"
              size="small"
              icon={<UndoOutlined />}
              onClick={async () => {
                setRestoreLoading(true)
                try {
                  const result = await restoreRuns([record.id])
                  if (result.restored_count > 0) {
                    message.success(t('recycle_bin.restore_success', { count: 1 }))
                    fetchDeletedRuns()
                    onRestore?.()
                  }
                } catch (error) {
                  message.error(t('recycle_bin.restore_failed'))
                } finally {
                  setRestoreLoading(false)
                }
              }}
            />
          </Tooltip>
          <Tooltip title={t('recycle_bin.preview_assets')}>
            <Button 
              type="text"
              size="small"
              icon={<FileOutlined />}
              onClick={() => fetchAssetRefs(record.id)}
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
          <span>{t('recycle_bin.title')}</span>
          <Tag color="orange">{deletedRuns.length}</Tag>
        </Space>
      }
      open={open}
      onCancel={onClose}
      width={950}
      footer={[
        <Button key="close" onClick={onClose}>
          {t('experiments.cancel')}
        </Button>,
        <Button 
          key="restore" 
          type="primary"
          icon={<UndoOutlined />}
          loading={restoreLoading}
          disabled={selectedRowKeys.length === 0}
          onClick={handleRestore}
        >
          {t('recycle_bin.restore_selected')} 
          {selectedRowKeys.length > 0 && ` (${selectedRowKeys.length})`}
        </Button>,
        <Popconfirm
          key="permanent"
          title={t('recycle_bin.permanent_delete_title')}
          description={
            <div style={{ maxWidth: 300 }}>
              <p>{t('recycle_bin.permanent_delete_desc')}</p>
              <p style={{ color: '#ff4d4f', fontWeight: 500 }}>
                {t('recycle_bin.permanent_delete_warning')}
              </p>
            </div>
          }
          okText={t('recycle_bin.permanent_delete_confirm')}
          okType="danger"
          cancelText={t('experiments.cancel')}
          onConfirm={handlePermanentDelete}
          icon={<ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />}
        >
          <Button 
            danger
            icon={<DeleteOutlined />}
            loading={permanentDeleteLoading}
            disabled={selectedRowKeys.length === 0}
          >
            {t('recycle_bin.permanent_delete')}
            {selectedRowKeys.length > 0 && ` (${selectedRowKeys.length})`}
          </Button>
        </Popconfirm>,
        <Popconfirm
          key="empty"
          title={t('recycle_bin.empty_confirm_title')}
          description={
            <div style={{ maxWidth: 300 }}>
              <p>{t('recycle_bin.empty_confirm_desc')}</p>
              <p style={{ color: '#ff4d4f', fontWeight: 500 }}>
                {t('recycle_bin.permanent_delete_warning')}
              </p>
            </div>
          }
          okText={t('recycle_bin.empty_confirm')}
          okType="danger"
          cancelText={t('experiments.cancel')}
          onConfirm={handleEmptyBin}
          icon={<ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />}
        >
          <Button 
            danger
            type="primary"
            icon={<ClearOutlined />}
            loading={emptyLoading}
            disabled={deletedRuns.length === 0}
          >
            {t('recycle_bin.empty_bin')}
          </Button>
        </Popconfirm>
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message={t('recycle_bin.description')}
          description={t('recycle_bin.permanent_delete_info')}
          type="info"
          icon={<InfoCircleOutlined />}
          showIcon
        />
        
        <Table
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as string[]),
          }}
          dataSource={deletedRuns}
          columns={columns}
          loading={loading}
          rowKey="id"
          size="small"
          pagination={{
            pageSize: 8,
            showSizeChanger: false,
            showTotal: (total, range) => 
              t('recycle_bin.table_total', { from: range[0], to: range[1], total })
          }}
          locale={{
            emptyText: (
              <div style={{ padding: 20, textAlign: 'center' }}>
                <Typography.Text type="secondary">
                  {t('recycle_bin.empty_state')}
                </Typography.Text>
              </div>
            )
          }}
        />
        
        {/* Asset preview panel */}
        {previewRunId && (
          <div style={{ 
            border: `1px solid ${token.colorBorder}`, 
            borderRadius: 8, 
            padding: 16,
            background: token.colorBgContainer,
          }}>
            <Typography.Title level={5} style={{ marginTop: 0 }}>
              <FileOutlined /> {t('recycle_bin.asset_preview')}: {previewRunId}
            </Typography.Title>
            
            {previewLoading ? (
              <div style={{ textAlign: 'center', padding: 20 }}>
                <Spin />
              </div>
            ) : assetRefs ? (
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label={t('recycle_bin.orphaned_assets')} span={2}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    {assetRefs.orphaned_assets.length === 0 ? (
                      <Typography.Text type="secondary">
                        {t('recycle_bin.no_orphaned')}
                      </Typography.Text>
                    ) : (
                      assetRefs.orphaned_assets.map((a, i) => (
                        <Tag key={i} color="red">
                          [{a.asset_type}] {a.name || (a.fingerprint?.slice(0, 12) + '...')}
                        </Tag>
                      ))
                    )}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label={t('recycle_bin.shared_assets')} span={2}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    {assetRefs.shared_assets.length === 0 ? (
                      <Typography.Text type="secondary">
                        {t('recycle_bin.no_shared')}
                      </Typography.Text>
                    ) : (
                      assetRefs.shared_assets.map((a, i) => (
                        <Tooltip key={i} title={`Referenced by ${a.ref_count} runs`}>
                          <Tag color="green">
                            [{a.asset_type}] {a.name || (a.fingerprint?.slice(0, 12) + '...')} ({a.ref_count} refs)
                          </Tag>
                        </Tooltip>
                      ))
                    )}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label={t('recycle_bin.will_delete')}>
                  <Typography.Text type="danger">
                    {assetRefs.orphaned_count} {t('recycle_bin.assets')}
                  </Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label={t('recycle_bin.will_keep')}>
                  <Typography.Text type="success">
                    {assetRefs.shared_count} {t('recycle_bin.assets')}
                  </Typography.Text>
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <Typography.Text type="secondary">
                {t('recycle_bin.no_asset_info')}
              </Typography.Text>
            )}
          </div>
        )}
        
        {selectedRowKeys.length > 0 && (
          <Alert
            message={t('recycle_bin.selection_info', { count: selectedRowKeys.length })}
            type="info"
            style={{ marginTop: 8 }}
          />
        )}
      </Space>
    </Modal>
  )
}
