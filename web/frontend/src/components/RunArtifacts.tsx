import React, { useState, useEffect } from 'react'
import { Table, Tag, Button, Space, Tooltip, Empty, Spin, message, Tabs } from 'antd'
import { FileOutlined, DatabaseOutlined, SettingOutlined, CodeOutlined, AppstoreOutlined, RocketOutlined, ExperimentOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { formatFileSize, formatTimestamp } from '../utils/format'
import logger from '../utils/logger'

const { TabPane } = Tabs

interface ArtifactSummary {
  name: string
  type: string
  version: number
  size_bytes: number
  created_at: number
  description?: string
  aliases: string[]
  lifecycle_stage?: string
}

interface RunArtifactsProps {
  runId: string
}

// Get icon for artifact type
const getTypeIcon = (type: string) => {
  switch (type) {
    case 'model':
      return <RocketOutlined />
    case 'dataset':
      return <DatabaseOutlined />
    case 'config':
      return <SettingOutlined />
    case 'code':
      return <CodeOutlined />
    default:
      return <AppstoreOutlined />
  }
}

// Get lifecycle stage color
const getStageColor = (stage?: string) => {
  switch (stage) {
    case 'production':
      return 'green'
    case 'staging':
      return 'blue'
    case 'experimental':
      return 'orange'
    case 'archived':
      return 'default'
    default:
      return 'default'
  }
}

export default function RunArtifacts({ runId }: RunArtifactsProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [createdArtifacts, setCreatedArtifacts] = useState<ArtifactSummary[]>([])
  const [usedArtifacts, setUsedArtifacts] = useState<ArtifactSummary[]>([])

  useEffect(() => {
    loadArtifacts()
  }, [runId])

  const loadArtifacts = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/runs/${runId}/artifacts`)
      if (!response.ok) {
        const errorText = await response.text()
        logger.error(`API error: ${response.status} ${response.statusText}`, errorText)
        throw new Error(`Failed to load artifacts: ${response.statusText}`)
      }
      const data = await response.json()
      logger.info('Loaded artifacts:', data)
      setCreatedArtifacts(data.created || [])
      setUsedArtifacts(data.used || [])
    } catch (error) {
      logger.error('Failed to load run artifacts:', error)
      message.error(`Failed to load artifacts: ${error}`)
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: t('artifacts.name'),
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: ArtifactSummary) => (
        <Space>
          {getTypeIcon(record.type)}
          <a onClick={() => navigate(`/artifacts/${name}`)}>
            {name}
          </a>
        </Space>
      ),
    },
    {
      title: t('artifacts.version'),
      dataIndex: 'version',
      key: 'version',
      width: 100,
      render: (version: number) => (
        <Tag>v{version}</Tag>
      ),
    },
    {
      title: t('artifacts.aliases'),
      dataIndex: 'aliases',
      key: 'aliases',
      render: (aliases: string[]) => (
        <Space size={4}>
          {aliases.map(alias => (
            <Tag key={alias} color="blue">{alias}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('artifacts.stage'),
      dataIndex: 'lifecycle_stage',
      key: 'lifecycle_stage',
      render: (stage?: string) => stage && (
        <Tag color={getStageColor(stage)}>
          {t(`artifacts.stage.${stage}`)}
        </Tag>
      ),
    },
    {
      title: t('artifacts.size'),
      dataIndex: 'size_bytes',
      key: 'size_bytes',
      width: 100,
      render: (size: number) => formatFileSize(size),
    },
    {
      title: t('artifacts.created'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (timestamp: number) => formatTimestamp(timestamp),
    },
    {
      title: t('actions'),
      key: 'actions',
      width: 100,
      render: (_: any, record: ArtifactSummary) => (
        <Button
          type="link"
          size="small"
          onClick={() => navigate(`/artifacts/${record.name}?version=${record.version}`)}
        >
          {t('view')}
        </Button>
      ),
    },
  ]

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <Tabs defaultActiveKey="created">
      <TabPane 
        tab={
          <span>
            <RocketOutlined /> {t('run.artifacts.created')} ({createdArtifacts.length})
          </span>
        }
        key="created"
      >
        {createdArtifacts.length > 0 ? (
          <Table
            dataSource={createdArtifacts}
            columns={columns}
            rowKey={record => `${record.name}-v${record.version}`}
            size="small"
            pagination={{ pageSize: 10 }}
          />
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={t('run.artifacts.no_created')}
          />
        )}
      </TabPane>
      
      <TabPane
        tab={
          <span>
            <ExperimentOutlined /> {t('run.artifacts.used')} ({usedArtifacts.length})
          </span>
        }
        key="used"
      >
        {usedArtifacts.length > 0 ? (
          <Table
            dataSource={usedArtifacts}
            columns={columns}
            rowKey={record => `${record.name}-v${record.version}`}
            size="small"
            pagination={{ pageSize: 10 }}
          />
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={t('run.artifacts.no_used')}
          />
        )}
      </TabPane>
    </Tabs>
  )
}
