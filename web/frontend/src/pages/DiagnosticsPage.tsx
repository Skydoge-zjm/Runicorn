import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Empty, Space, Spin, Tabs, Tag, Typography, App } from 'antd'
import { ArrowLeftOutlined, BugOutlined, DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import LogsViewer from '../components/LogsViewer'
import {
  buildDiagnosticsDownloadUrl,
  buildDiagnosticsWsUrl,
  listDiagnosticsSources,
} from '../api/diagnostics'
import type { DiagnosticsSource, DiagnosticsSourcesResponse } from '../types/diagnostics'

const { Paragraph, Text, Title } = Typography

export default function DiagnosticsPage() {
  const { t } = useTranslation()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<DiagnosticsSourcesResponse | null>(null)
  const [selectedSourceId, setSelectedSourceId] = useState<string>('')

  const loadSources = async () => {
    setLoading(true)
    try {
      const nextData = await listDiagnosticsSources()
      setData(nextData)
      const querySource = searchParams.get('source')
      const availableSourceIds = new Set(nextData.sources.map(source => source.id))
      const nextSource = querySource && availableSourceIds.has(querySource)
        ? querySource
        : (availableSourceIds.has(selectedSourceId) ? selectedSourceId : nextData.defaultSource)
      setSelectedSourceId(nextSource)
    } catch (error) {
      const messageText = error instanceof Error ? error.message : t('diagnostics.load_failed')
      message.error(messageText)
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSources()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const querySource = searchParams.get('source')
    if (
      querySource &&
      querySource !== selectedSourceId &&
      data?.sources.some(source => source.id === querySource)
    ) {
      setSelectedSourceId(querySource)
    }
  }, [data?.sources, searchParams, selectedSourceId])

  const selectedSource: DiagnosticsSource | undefined = useMemo(
    () => data?.sources.find(source => source.id === selectedSourceId) ?? data?.sources[0],
    [data, selectedSourceId],
  )

  const logUrl = useMemo(
    () => (selectedSource ? buildDiagnosticsWsUrl(selectedSource.id) : ''),
    [selectedSource],
  )

  const handleSelectSource = (sourceId: string) => {
    setSelectedSourceId(sourceId)
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('source', sourceId)
    setSearchParams(nextParams, { replace: true })
  }

  const goBack = () => {
    if (window.history.length > 1) {
      navigate(-1)
      return
    }
    navigate('/')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', padding: 16 }}>
      <div style={{ flexShrink: 0, marginBottom: 16 }}>
        <Space style={{ marginBottom: 12 }} wrap>
          <Button icon={<ArrowLeftOutlined />} onClick={goBack}>
            {t('diagnostics.back')}
          </Button>
        </Space>
        <Title level={2} style={{ marginBottom: 8 }}>
          <BugOutlined /> {t('diagnostics.title')}
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          {t('diagnostics.subtitle')}
        </Paragraph>
      </div>

      <div style={{ flexShrink: 0, marginBottom: 16 }}>
        <Alert
          type={data?.remoteMode ? 'warning' : 'info'}
          showIcon
          message={data?.remoteMode ? t('diagnostics.scope.remote') : t('diagnostics.scope.local')}
          description={data?.remoteMode ? t('diagnostics.remote_help') : t('diagnostics.local_help')}
        />
      </div>

      <Card
        title={
          <Space>
            <span>{t('diagnostics.logs_title')}</span>
            {selectedSource && !selectedSource.available && (
              <Tag color="default">{t('diagnostics.status.waiting')}</Tag>
            )}
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void loadSources()}>
              {t('diagnostics.refresh')}
            </Button>
            <Button
              icon={<DownloadOutlined />}
              disabled={!selectedSource}
              onClick={() => {
                if (!selectedSource) return
                window.open(buildDiagnosticsDownloadUrl(selectedSource.id), '_blank', 'noopener,noreferrer')
              }}
            >
              {t('diagnostics.download')}
            </Button>
          </Space>
        }
        styles={{ body: { display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 } }}
        style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}
      >
        {loading ? (
          <div style={{ padding: 24, textAlign: 'center' }}>
            <Spin size="large" />
          </div>
        ) : !data || data.sources.length === 0 ? (
          <Empty description={t('diagnostics.empty')} />
        ) : (
          <>
            <Tabs
              activeKey={selectedSource?.id}
              onChange={handleSelectSource}
              items={data.sources.map(source => ({
                key: source.id,
                label: t(`diagnostics.source.${source.kind}`),
              }))}
            />
            {selectedSource && (
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary">{t('diagnostics.path')}:</Text>{' '}
                <Text code copyable>{selectedSource.path}</Text>
              </div>
            )}
            {selectedSource ? (
              <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
                <LogsViewer key={selectedSource.id} url={logUrl} />
              </div>
            ) : (
              <Empty description={t('diagnostics.empty')} />
            )}
          </>
        )}
      </Card>
    </div>
  )
}
