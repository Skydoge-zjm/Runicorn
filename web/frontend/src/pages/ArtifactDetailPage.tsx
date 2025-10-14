import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card, Descriptions, Space, Tag, Button, Table, Tabs, message, Typography,
  Row, Col, Statistic, Alert, Tooltip, Badge, Empty, Modal
} from 'antd'
import {
  ArrowLeftOutlined, HistoryOutlined, FileOutlined, ShareAltOutlined,
  DownloadOutlined, DeleteOutlined, CodeOutlined, TagOutlined,
  ClockCircleOutlined, UserOutlined, DatabaseOutlined, InfoCircleOutlined,
  ThunderboltOutlined, LineChartOutlined
} from '@ant-design/icons'
import {
  getArtifactDetail,
  listArtifactVersions,
  getArtifactFiles,
  getArtifactLineage,
  deleteArtifactVersion,
  remoteDownloadArtifact,
  getStorageMode
} from '../api'
import { RunDetailSkeleton } from '../components/LoadingSkeleton'
import LineageGraph from '../components/LineageGraph'
import DownloadProgressModal from '../components/DownloadProgressModal'
import ArtifactTrainingHistory from '../components/ArtifactTrainingHistory'
import ArtifactPerformanceChart from '../components/ArtifactPerformanceChart'
import logger from '../utils/logger'
import designTokens from '../styles/designTokens'

const { Text, Title, Paragraph } = Typography
const { TabPane } = Tabs

const ArtifactDetailPage: React.FC = () => {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation()
  
  const [loading, setLoading] = useState(false)
  const [currentVersion, setCurrentVersion] = useState<number | null>(null)
  const [detail, setDetail] = useState<any>(null)
  const [versions, setVersions] = useState<any[]>([])
  const [files, setFiles] = useState<any>(null)
  const [lineage, setLineage] = useState<any>(null)
  const [lineageLoading, setLineageLoading] = useState(false)
  
  // Remote storage and download states
  const [isRemote, setIsRemote] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [downloadTaskId, setDownloadTaskId] = useState<string | null>(null)
  const [downloadModalVisible, setDownloadModalVisible] = useState(false)

  // Format bytes
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
  }

  // Format date
  const formatDate = (timestamp: number): string => {
    return new Date(timestamp * 1000).toLocaleString()
  }

  // Fetch versions list
  const fetchVersions = useCallback(async () => {
    if (!name) return
    
    try {
      const data = await listArtifactVersions(name)
      setVersions(data || [])
      
      // Set current version to latest if not set
      if (!currentVersion && data && data.length > 0) {
        setCurrentVersion(data[data.length - 1].version)
      }
    } catch (error) {
      logger.error('Failed to fetch versions:', error)
      message.error(t('Failed to fetch versions'))
    }
  }, [name, currentVersion, t])

  // Fetch artifact detail
  const fetchDetail = useCallback(async () => {
    if (!name || !currentVersion) return
    
    setLoading(true)
    try {
      const data = await getArtifactDetail(name, currentVersion)
      setDetail(data)
    } catch (error) {
      logger.error('Failed to fetch artifact detail:', error)
      message.error(t('Failed to fetch artifact details'))
    } finally {
      setLoading(false)
    }
  }, [name, currentVersion, t])

  // Fetch files
  const fetchFiles = useCallback(async () => {
    if (!name || !currentVersion) return
    
    try {
      const data = await getArtifactFiles(name, currentVersion)
      setFiles(data)
    } catch (error) {
      logger.error('Failed to fetch files:', error)
    }
  }, [name, currentVersion])

  // Fetch lineage
  const fetchLineage = useCallback(async () => {
    if (!name || !currentVersion) return
    
    setLineageLoading(true)
    try {
      const data = await getArtifactLineage(name, currentVersion, undefined, 3)
      setLineage(data)
    } catch (error) {
      logger.error('Failed to fetch lineage:', error)
    } finally {
      setLineageLoading(false)
    }
  }, [name, currentVersion])

  useEffect(() => {
    fetchVersions()
  }, [fetchVersions])

  useEffect(() => {
    if (currentVersion) {
      fetchDetail()
      fetchFiles()
    }
  }, [fetchDetail, fetchFiles])

  // Delete version
  const handleDelete = async (version: number) => {
    Modal.confirm({
      title: t('artifacts.delete_confirm', { name, version }),
      content: t('artifacts.delete_warning'),
      okText: t('artifacts.delete'),
      okType: 'danger',
      cancelText: t('experiments.cancel'),
      onOk: async () => {
        try {
          await deleteArtifactVersion(name!, version)
          message.success(t('Deleted successfully'))
          fetchVersions()
          
          // If deleted current version, switch to latest
          if (version === currentVersion) {
            const remaining = versions.filter(v => v.version !== version)
            if (remaining.length > 0) {
              setCurrentVersion(remaining[remaining.length - 1].version)
            } else {
              navigate('/artifacts')
            }
          }
        } catch (error) {
          logger.error('Failed to delete:', error)
          message.error(t('Delete failed'))
        }
      }
    })
  }

  // Show skeleton on initial load
  if (loading && !detail) {
    return <RunDetailSkeleton />
  }

  if (!detail) {
    return (
      <Card>
        <Empty description={t('artifact.detail.title', { name })} />
      </Card>
    )
  }

  // Version selector dropdown
  const versionOptions = versions.map(v => ({
    label: `v${v.version} (${formatDate(v.created_at)})`,
    value: v.version
  }))

  // Files table columns
  const fileColumns = [
    {
      title: t('artifact.files.name'),
      dataIndex: 'path',
      key: 'path',
      render: (path: string, record: any) => (
        <Space direction="vertical" size={0}>
          <Text strong>{path}</Text>
          {record.absolute_path && (
            <Tooltip title={t('Click to copy path')}>
              <Text 
                code 
                copyable={{ text: record.absolute_path }}
                style={{ fontSize: designTokens.typography.fontSize.xs }}
              >
                {record.absolute_path}
              </Text>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: t('artifact.files.size'),
      dataIndex: 'size',
      key: 'size',
      width: 120,
      render: (size: number) => formatBytes(size),
    },
    {
      title: t('artifact.files.hash'),
      dataIndex: 'digest',
      key: 'digest',
      width: 200,
      render: (digest: string) => (
        <Tooltip title={digest}>
          <Text code style={{ fontSize: designTokens.typography.fontSize.xs }}>
            {digest.split(':')[1]?.substring(0, 16)}...
          </Text>
        </Tooltip>
      ),
    },
  ]

  // Version history table columns
  const versionColumns = [
    {
      title: t('artifact.versions.version'),
      dataIndex: 'version',
      key: 'version',
      width: 100,
      render: (v: number) => (
        <Tag color={v === currentVersion ? 'blue' : 'default'}>
          v{v}
        </Tag>
      ),
    },
    {
      title: t('artifact.versions.date'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (timestamp: number) => formatDate(timestamp),
    },
    {
      title: t('artifact.versions.run'),
      dataIndex: 'created_by_run',
      key: 'created_by_run',
      render: (runId: string) => (
        <Tooltip title="Click to view run">
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/runs/${runId}`)}
          >
            {runId.substring(0, 16)}...
          </Button>
        </Tooltip>
      ),
    },
    {
      title: t('artifact.versions.size'),
      dataIndex: 'size_bytes',
      key: 'size',
      width: 120,
      render: (size: number) => formatBytes(size),
    },
    {
      title: t('artifact.versions.files'),
      dataIndex: 'num_files',
      key: 'num_files',
      width: 80,
    },
    {
      title: t('Aliases'),
      dataIndex: 'aliases',
      key: 'aliases',
      render: (aliases: string[]) => (
        <Space size={4} wrap>
          {aliases.map(alias => (
            <Tag key={alias} color="blue" style={{ fontSize: designTokens.typography.fontSize.xs }}>
              {alias}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('artifact.versions.actions'),
      key: 'actions',
      width: 150,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button
            size="small"
            type={record.version === currentVersion ? 'primary' : 'default'}
            onClick={() => setCurrentVersion(record.version)}
          >
            {t('View')}
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.version)}
          />
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: designTokens.spacing.lg }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Back Button */}
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/artifacts')}
        >
          {t('Back to Artifacts')}
        </Button>

        {/* Header */}
        <Card>
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Space>
              <Title level={2} style={{ margin: 0 }}>
                {t('artifact.detail.title', { name })}
              </Title>
              <Tag color={designTokens.colors.primary}>
                {t('artifact.detail.version', { version: currentVersion })}
              </Tag>
              <Tag icon={<DatabaseOutlined />}>
                {t(`artifacts.type.${detail.type}`)}
              </Tag>
            </Space>
            
            {detail.description && (
              <Paragraph type="secondary">{detail.description}</Paragraph>
            )}
          </Space>
        </Card>

        {/* Summary Statistics */}
        <Row gutter={[designTokens.spacing.md, designTokens.spacing.md]}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={t('artifact.detail.size')}
                value={formatBytes(detail.size_bytes)}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={t('artifact.detail.files_count')}
                value={detail.num_files}
                prefix={<FileOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={t('Total Versions')}
                value={versions.length}
                prefix={<HistoryOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={t('artifact.detail.created_at')}
                value={formatDate(detail.created_at)}
                valueStyle={{ fontSize: designTokens.typography.fontSize.sm }}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>

        {/* Tabs */}
        <Card>
          <Tabs defaultActiveKey="info">
            {/* Info Tab */}
            <TabPane tab={<><InfoCircleOutlined /> {t('Info')}</>} key="info">
              <Descriptions bordered column={2} size="small">
                <Descriptions.Item label={t('artifact.detail.type')}>
                  {t(`artifacts.type.${detail.type}`)}
                </Descriptions.Item>
                <Descriptions.Item label={t('artifact.detail.status')}>
                  <Tag color="success">{detail.status}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label={t('artifact.detail.created_by')}>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => navigate(`/runs/${detail.created_by_run}`)}
                  >
                    {detail.created_by_run}
                  </Button>
                </Descriptions.Item>
                <Descriptions.Item label={t('artifact.detail.created_at')}>
                  {formatDate(detail.created_at)}
                </Descriptions.Item>
                <Descriptions.Item label={t('artifact.detail.size')}>
                  {formatBytes(detail.size_bytes)}
                </Descriptions.Item>
                <Descriptions.Item label={t('artifact.detail.files_count')}>
                  {detail.num_files} files, {detail.num_references} references
                </Descriptions.Item>
              </Descriptions>

              {/* Metadata */}
              {detail.metadata && Object.keys(detail.metadata).length > 0 && (
                <div style={{ marginTop: designTokens.spacing.lg }}>
                  <Title level={5}>{t('artifact.detail.metadata')}</Title>
                  <Card size="small">
                    <pre style={{ margin: 0, fontSize: designTokens.typography.fontSize.sm }}>
                      {JSON.stringify(detail.metadata, null, 2)}
                    </pre>
                  </Card>
                </div>
              )}

              {/* Tags */}
              {detail.tags && detail.tags.length > 0 && (
                <div style={{ marginTop: designTokens.spacing.md }}>
                  <Title level={5}>{t('artifact.detail.tags')}</Title>
                  <Space size={[8, 8]} wrap>
                    {detail.tags.map((tag: string) => (
                      <Tag key={tag} icon={<TagOutlined />} color="blue">
                        {tag}
                      </Tag>
                    ))}
                  </Space>
                </div>
              )}
            </TabPane>

            {/* Files Tab */}
            <TabPane tab={<><FileOutlined /> {t('artifact.files.title')} ({files?.files?.length || 0})</>} key="files">
              <Table
                dataSource={files?.files || []}
                columns={fileColumns}
                rowKey="path"
                size="small"
                pagination={false}
                locale={{
                  emptyText: (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description={t('artifact.files.no_files')}
                    />
                  )
                }}
              />

              {/* External References */}
              {files?.references && files.references.length > 0 && (
                <div style={{ marginTop: designTokens.spacing.lg }}>
                  <Title level={5}>{t('artifact.references.title')}</Title>
                  <Table
                    dataSource={files.references}
                    columns={[
                      {
                        title: t('artifact.references.uri'),
                        dataIndex: 'uri',
                        key: 'uri',
                      },
                      {
                        title: t('artifact.references.checksum'),
                        dataIndex: 'checksum',
                        key: 'checksum',
                        render: (checksum: string) => checksum || '-',
                      },
                    ]}
                    size="small"
                    pagination={false}
                  />
                </div>
              )}
            </TabPane>

            {/* Version History Tab */}
            <TabPane tab={<><HistoryOutlined /> {t('artifact.versions.title')} ({versions.length})</>} key="versions">
              <Table
                dataSource={versions}
                columns={versionColumns}
                rowKey="version"
                size="small"
                pagination={{ pageSize: 10 }}
              />
            </TabPane>

            {/* Training History Tab */}
            <TabPane
              tab={<><ThunderboltOutlined /> {t('artifact.training.tab')}</>}
              key="training"
            >
              <ArtifactTrainingHistory 
                artifactName={name}
                artifactType={detail?.type}
                version={currentVersion}
              />
            </TabPane>

            {/* Performance Tab */}
            <TabPane
              tab={<><LineChartOutlined /> {t('artifact.performance.tab')}</>}
              key="performance"
            >
              <ArtifactPerformanceChart
                artifactName={name}
                artifactType={detail?.type}
              />
            </TabPane>

            {/* Lineage Tab */}
            <TabPane 
              tab={<><ShareAltOutlined /> {t('artifact.lineage.title')}</>} 
              key="lineage"
            >
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Alert
                  message={t('artifact.lineage.description')}
                  type="info"
                  showIcon
                  closable
                />
                
                {!lineage && !lineageLoading && (
                  <Button onClick={fetchLineage}>
                    {t('Load Lineage Graph')}
                  </Button>
                )}
                
                {lineageLoading && (
                  <Card loading />
                )}
                
                {lineage && (
                  <LineageGraph data={lineage} />
                )}
              </Space>
            </TabPane>
          </Tabs>
        </Card>
      </Space>
    </div>
  )
}

export default ArtifactDetailPage

