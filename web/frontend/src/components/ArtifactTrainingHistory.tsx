import React, { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Button, Space, Spin, Empty, message, Statistic, Row, Col } from 'antd'
import { PlayCircleOutlined, ClockCircleOutlined, ThunderboltOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { formatTimestamp, formatDuration } from '../utils/format'
import logger from '../utils/logger'

interface TrainingMetrics {
  run_id: string
  run_name: string
  project: string
  metrics: Record<string, any>
  created_at: number
  duration_seconds?: number
  status: string
}

interface ArtifactTrainingHistoryProps {
  artifactName: string
  artifactType?: string
  version?: number
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'finished':
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />
    case 'failed':
      return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
    case 'running':
      return <ThunderboltOutlined style={{ color: '#1890ff' }} />
    default:
      return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />
  }
}

export default function ArtifactTrainingHistory({ 
  artifactName, 
  artifactType,
  version 
}: ArtifactTrainingHistoryProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [trainingMetrics, setTrainingMetrics] = useState<TrainingMetrics | null>(null)

  useEffect(() => {
    loadTrainingMetrics()
  }, [artifactName, version])

  const loadTrainingMetrics = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (version) params.append('version', version.toString())
      if (artifactType) params.append('type', artifactType)

      const response = await fetch(`/api/artifacts/${artifactName}/training-metrics?${params}`)
      if (!response.ok) {
        if (response.status === 404) {
          setTrainingMetrics(null)
          return
        }
        throw new Error(`Failed to load training metrics: ${response.statusText}`)
      }
      
      const data = await response.json()
      setTrainingMetrics(data)
    } catch (error) {
      logger.error('Failed to load training metrics:', error)
      message.error(t('Failed to load training metrics'))
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (!trainingMetrics) {
    return (
      <Card>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('artifact.training.no_data')}
        />
      </Card>
    )
  }

  // Extract key metrics
  const keyMetrics = Object.entries(trainingMetrics.metrics)
    .filter(([_, value]) => typeof value === 'number')
    .slice(0, 6) // Show top 6 metrics

  return (
    <Card 
      title={
        <Space>
          <PlayCircleOutlined />
          {t('artifact.training.title')}
        </Space>
      }
      extra={
        <Button
          type="primary"
          onClick={() => navigate(`/runs/${trainingMetrics.run_id}`)}
        >
          {t('artifact.training.view_run')}
        </Button>
      }
    >
      <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label={t('artifact.training.run_name')}>
          <Space>
            {getStatusIcon(trainingMetrics.status)}
            <a onClick={() => navigate(`/runs/${trainingMetrics.run_id}`)}>
              {trainingMetrics.run_name}
            </a>
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label={t('artifact.training.project')}>
          <Tag>{trainingMetrics.project}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label={t('artifact.training.status')}>
          <Tag color={trainingMetrics.status === 'finished' ? 'success' : 'error'}>
            {t(`status.${trainingMetrics.status}`)}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label={t('artifact.training.duration')}>
          {trainingMetrics.duration_seconds 
            ? formatDuration(trainingMetrics.duration_seconds * 1000)
            : '-'
          }
        </Descriptions.Item>
        <Descriptions.Item label={t('artifact.training.created_at')} span={2}>
          {formatTimestamp(trainingMetrics.created_at)}
        </Descriptions.Item>
      </Descriptions>

      {keyMetrics.length > 0 && (
        <>
          <h4>{t('artifact.training.key_metrics')}</h4>
          <Row gutter={16}>
            {keyMetrics.map(([key, value]) => (
              <Col span={8} key={key} style={{ marginBottom: 16 }}>
                <Statistic
                  title={key}
                  value={value as number}
                  precision={typeof value === 'number' && value < 1 ? 4 : 2}
                />
              </Col>
            ))}
          </Row>
        </>
      )}
    </Card>
  )
}
