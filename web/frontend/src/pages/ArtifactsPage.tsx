import React, { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { 
  Card, Table, Space, Input, Select, Tag, Statistic, Row, Col, Button, 
  message, Empty, Tooltip, Typography, Badge, Alert 
} from 'antd'
import { 
  SearchOutlined, ReloadOutlined, DatabaseOutlined, FolderOutlined,
  FileOutlined, CodeOutlined, AppstoreOutlined, CloudOutlined,
  EyeOutlined, DownloadOutlined, DeleteOutlined, HistoryOutlined
} from '@ant-design/icons'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { listArtifacts, getArtifactsStats } from '../api'
import { GenericLoadingSkeleton } from '../components/LoadingSkeleton'
import FancyStatCard from '../components/fancy/FancyStatCard'
import FancyEmpty from '../components/fancy/FancyEmpty'
import { StaggerContainer, StaggerItem } from '../components/animations/PageTransition'
import logger from '../utils/logger'
import designTokens from '../styles/designTokens'
import { colorConfig } from '../config/animation_config'
import '../styles/enhanced-table.css'

const { Text, Title } = Typography

interface ArtifactData {
  name: string
  type: string
  num_versions: number
  latest_version: number
  size_bytes: number
  created_at: number
  updated_at: number
  aliases: Record<string, number>
}

const ArtifactsPage: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  
  const [artifacts, setArtifacts] = useState<ArtifactData[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [stats, setStats] = useState<any>(null)

  // Fetch artifacts
  const fetchArtifacts = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true)
    
    try {
      const filterType = typeFilter === 'all' ? undefined : typeFilter
      const data = await listArtifacts(filterType)
      setArtifacts(data || [])
    } catch (error) {
      logger.error('Failed to fetch artifacts:', error)
      message.error(t('Failed to fetch artifacts'))
    } finally {
      if (showLoading) setLoading(false)
    }
  }, [typeFilter, t])

  // Fetch stats
  const fetchStats = useCallback(async () => {
    try {
      const data = await getArtifactsStats()
      setStats(data)
    } catch (error) {
      logger.error('Failed to fetch artifact stats:', error)
    }
  }, [])

  useEffect(() => {
    fetchArtifacts()
    fetchStats()
  }, [fetchArtifacts, fetchStats])

  // Filter artifacts by search text
  const filteredArtifacts = artifacts.filter(artifact => {
    if (!searchText) return true
    const search = searchText.toLowerCase()
    return (
      artifact.name.toLowerCase().includes(search) ||
      artifact.type.toLowerCase().includes(search)
    )
  })

  // Statistics
  const artifactStats = {
    total: artifacts.length,
    models: artifacts.filter(a => a.type === 'model').length,
    datasets: artifacts.filter(a => a.type === 'dataset').length,
    total_size: artifacts.reduce((sum, a) => sum + a.size_bytes, 0),
  }

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

  // Get type icon
  const getTypeIcon = (type: string) => {
    const iconProps = { style: { fontSize: 16 } }
    switch (type) {
      case 'model':
        return <DatabaseOutlined {...iconProps} />
      case 'dataset':
        return <FolderOutlined {...iconProps} />
      case 'config':
        return <FileOutlined {...iconProps} />
      case 'code':
        return <CodeOutlined {...iconProps} />
      default:
        return <AppstoreOutlined {...iconProps} />
    }
  }

  // Get type color
  const getTypeColor = (type: string): string => {
    switch (type) {
      case 'model':
        return designTokens.colors.primary
      case 'dataset':
        return designTokens.colors.success
      case 'config':
        return designTokens.colors.warning
      case 'code':
        return designTokens.colors.info
      default:
        return '#8c8c8c'
    }
  }

  // Table columns
  const columns = [
    {
      title: t('artifacts.type'),
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => (
        <Tooltip title={t(`artifacts.type.${type}`)}>
          <Tag 
            icon={getTypeIcon(type)} 
            color={getTypeColor(type)}
          >
            {t(`artifacts.type.${type}`)}
          </Tag>
        </Tooltip>
      ),
      filters: [
        { text: t('artifacts.type.model'), value: 'model' },
        { text: t('artifacts.type.dataset'), value: 'dataset' },
        { text: t('artifacts.type.config'), value: 'config' },
        { text: t('artifacts.type.code'), value: 'code' },
        { text: t('artifacts.type.custom'), value: 'custom' },
      ],
      onFilter: (value: any, record: ArtifactData) => record.type === value,
    },
    {
      title: t('Name'),
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: ArtifactData) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ fontSize: designTokens.typography.fontSize.md }}>
            {name}
          </Text>
          <Space size="small">
            <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs }}>
              {t('artifacts.latest_version', { version: record.latest_version })}
            </Text>
            <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs }}>
              •
            </Text>
            <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs }}>
              {t('artifacts.versions_count', { count: record.num_versions })}
            </Text>
          </Space>
        </Space>
      ),
    },
    {
      title: t('artifacts.size'),
      dataIndex: 'size_bytes',
      key: 'size',
      width: 120,
      render: (size: number) => formatBytes(size),
      sorter: (a: ArtifactData, b: ArtifactData) => a.size_bytes - b.size_bytes,
    },
    {
      title: t('artifacts.updated'),
      dataIndex: 'updated_at',
      key: 'updated',
      width: 180,
      render: (timestamp: number) => formatDate(timestamp),
      sorter: (a: ArtifactData, b: ArtifactData) => a.updated_at - b.updated_at,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: t('artifacts.aliases'),
      dataIndex: 'aliases',
      key: 'aliases',
      width: 150,
      render: (aliases: Record<string, number>) => (
        <Space size={4} wrap>
          {Object.keys(aliases).slice(0, 3).map(alias => (
            <Tag key={alias} color="blue" style={{ fontSize: designTokens.typography.fontSize.xs }}>
              {alias}
            </Tag>
          ))}
          {Object.keys(aliases).length > 3 && (
            <Tag style={{ fontSize: designTokens.typography.fontSize.xs }}>
              +{Object.keys(aliases).length - 3}
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('table.actions'),
      key: 'actions',
      width: 200,
      render: (_: any, record: ArtifactData) => (
        <Space size="small">
          <Tooltip title={t('artifacts.view_versions')}>
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/artifacts/${record.name}`)}
            >
              {t('View')}
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ]

  // Show skeleton on initial load
  if (loading && artifacts.length === 0) {
    return <GenericLoadingSkeleton rows={8} />
  }

  return (
    <div style={{ padding: designTokens.spacing.lg }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <div>
          <Title level={2} style={{ marginBottom: designTokens.spacing.sm }}>
            {t('artifacts.title')}
          </Title>
          <Text type="secondary">{t('artifacts.description')}</Text>
        </div>

        {/* Statistics Cards */}
        {stats && (
          <Row gutter={[designTokens.spacing.md, designTokens.spacing.md]}>
            <Col xs={24} sm={12} md={6}>
              <FancyStatCard
                title={t('artifacts.stats.total')}
                value={stats.total_artifacts || 0}
                icon={<DatabaseOutlined />}
                gradientColors={colorConfig.gradients.primary}
              />
            </Col>
            <Col xs={24} sm={12} md={6}>
              <FancyStatCard
                title={t('artifacts.stats.total_versions')}
                value={stats.total_versions || 0}
                icon={<HistoryOutlined />}
                gradientColors={colorConfig.gradients.info}
              />
            </Col>
            <Col xs={24} sm={12} md={6}>
              <FancyStatCard
                title={t('artifacts.stats.total_size')}
                value={stats.total_size_bytes || 0}
                formattedValue={formatBytes(stats.total_size_bytes || 0)}
                icon={<CloudOutlined />}
                gradientColors={colorConfig.gradients.success}
              />
            </Col>
            <Col xs={24} sm={12} md={6}>
              <FancyStatCard
                title={t('artifacts.stats.dedup_saved')}
                value={stats.space_saved_bytes || 0}
                formattedValue={stats.dedup_enabled ? formatBytes(stats.space_saved_bytes || 0) : 'N/A'}
                subtitle={stats.dedup_enabled && stats.dedup_ratio ? `${(stats.dedup_ratio * 100).toFixed(1)}% saved` : undefined}
                icon={<AppstoreOutlined />}
                gradientColors={colorConfig.gradients.warning}
              />
            </Col>
          </Row>
        )}

        {/* Filters and Search */}
        <Card size="small">
          <Space wrap>
            <Input
              placeholder={t('artifacts.search_placeholder')}
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 300 }}
              allowClear
            />
            <Select
              value={typeFilter}
              onChange={setTypeFilter}
              style={{ width: 150 }}
              options={[
                { label: t('artifacts.type.all'), value: 'all' },
                { label: t('artifacts.type.model'), value: 'model' },
                { label: t('artifacts.type.dataset'), value: 'dataset' },
                { label: t('artifacts.type.config'), value: 'config' },
                { label: t('artifacts.type.code'), value: 'code' },
                { label: t('artifacts.type.custom'), value: 'custom' },
              ]}
            />
            <Button
              icon={<ReloadOutlined spin={loading} />}
              onClick={() => { fetchArtifacts(); fetchStats(); }}
              loading={loading}
            >
              {t('runs.refresh')}
            </Button>
          </Space>
        </Card>

        {/* Type Distribution */}
        {stats && stats.by_type && Object.keys(stats.by_type).length > 0 && (
          <Alert
            message={
              <Space>
                <Text>Type Distribution:</Text>
                {Object.entries(stats.by_type).map(([type, data]: [string, any]) => (
                  <Badge 
                    key={type}
                    count={data.count}
                    showZero
                    color={getTypeColor(type)}
                    overflowCount={9999}
                    style={{ marginLeft: 8 }}
                  >
                    <Tag icon={getTypeIcon(type)}>{t(`artifacts.type.${type}`)}</Tag>
                  </Badge>
                ))}
              </Space>
            }
            type="info"
            showIcon={false}
            style={{ marginBottom: designTokens.spacing.md }}
          />
        )}

        {/* Artifacts Table */}
        <Card>
          <Table
            dataSource={filteredArtifacts}
            columns={columns}
            rowKey="name"
            loading={loading}
            pagination={{
              pageSize: 10,
              showTotal: (total, range) => 
                t('experiments.table_total', { from: range[0], to: range[1], total }),
              showSizeChanger: true,
              showQuickJumper: true,
            }}
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <Space direction="vertical" size="small">
                      <Text type="secondary">{t('artifacts.no_artifacts')}</Text>
                      <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs }}>
                        {t('artifacts.create_first')}
                      </Text>
                    </Space>
                  }
                />
              )
            }}
          />
        </Card>

        {/* Usage Guide */}
        {artifacts.length === 0 && !loading && (
          <Card 
            title={
              <Space>
                <CodeOutlined />
                <span>Quick Start Guide</span>
              </Space>
            }
          >
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <div>
                <Text strong>1. Save a model as artifact:</Text>
                <pre style={{ 
                  background: '#f5f5f5', 
                  padding: designTokens.spacing.md, 
                  borderRadius: designTokens.borderRadius.md,
                  marginTop: designTokens.spacing.sm 
                }}>
{`import runicorn as rn

run = rn.init(project="my_project")

# Create artifact
artifact = rn.Artifact("my-model", type="model")
artifact.add_file("model.pth")
artifact.add_metadata({"accuracy": 0.95})

# Save with version control
run.log_artifact(artifact)  # → v1
run.finish()`}
                </pre>
              </div>

              <div>
                <Text strong>2. Use a saved artifact:</Text>
                <pre style={{ 
                  background: '#f5f5f5', 
                  padding: designTokens.spacing.md, 
                  borderRadius: designTokens.borderRadius.md,
                  marginTop: designTokens.spacing.sm 
                }}>
{`import runicorn as rn

run = rn.init(project="inference")

# Load latest version
artifact = run.use_artifact("my-model:latest")
model_path = artifact.download()

# Use the model...
run.finish()`}
                </pre>
              </div>
            </Space>
          </Card>
        )}
      </Space>
    </div>
  )
}

export default ArtifactsPage

