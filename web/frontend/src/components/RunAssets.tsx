import React, { useState, useEffect, useMemo } from 'react'
import { Card, Collapse, Empty, Spin, message, Space, Tag, Typography, Button } from 'antd'
import { DatabaseOutlined, SettingOutlined, CodeOutlined, RocketOutlined, DownloadOutlined, EyeOutlined, CopyOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { downloadRunAssetUrl, getRunAssets } from '../api'
import logger from '../utils/logger'
import { parseRunAssetsPayload, ParsedAsset } from '../utils/assetParse'
import { encodeAssetIdentity } from '../utils/assetIdentity'
import { useNavigate } from 'react-router-dom'
import { suggestAssetDownloadFilename } from '../utils/assetDownload'

interface RunAssetsProps {
  runId: string
}

export default function RunAssets({ runId }: RunAssetsProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { Text } = Typography
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    loadAssets()
  }, [runId])

  const loadAssets = async () => {
    setLoading(true)
    try {
      const res = await getRunAssets(runId)
      setData(res)
    } catch (error) {
      logger.error('Failed to load run assets:', error)
      message.error(`${t('assets.errors.failed_to_load_assets') || 'Failed to load assets'}: ${error}`)
    } finally {
      setLoading(false)
    }
  }

  const parsed: ParsedAsset[] = useMemo(() => parseRunAssetsPayload(data), [data])

  const groups = useMemo(() => {
    const by: Record<string, ParsedAsset[]> = { code: [], config: [], dataset: [], pretrained: [], output: [] }
    parsed.forEach((a) => {
      by[a.kind] = by[a.kind] || []
      by[a.kind].push(a)
    })
    return by
  }, [parsed])

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      message.success(t('common.copied') || 'Copied')
    } catch {
      message.error(t('common.copy_failed') || 'Failed to copy')
    }
  }

  const renderAssetRow = (a: ParsedAsset) => {
    const encoded = encodeAssetIdentity(a.identity)
    const href = a.archive_path ? downloadRunAssetUrl(runId, a.archive_path, suggestAssetDownloadFilename(a)) : null
    return (
      <Card key={`${a.kind}:${a.name}:${encoded}`} size="small" style={{ marginBottom: 10 }}>
        <RowLine
          left={
            <Space wrap>
              {a.kind === 'code' && <CodeOutlined />}
              {a.kind === 'config' && <SettingOutlined />}
              {a.kind === 'dataset' && <DatabaseOutlined />}
              {a.kind === 'pretrained' && <RocketOutlined />}
              {a.kind === 'output' && <Tag>{t('assets.kind.output') || 'output'}</Tag>}
              <Text strong>{a.name}</Text>
              {a.saved ? <Tag color="green">{t('assets.tag.saved') || 'saved'}</Tag> : <Tag>{t('assets.tag.ref') || 'ref'}</Tag>}
            </Space>
          }
          right={
            <Space wrap>
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={() => navigate(`/assets/${encoded}`, { state: { fromRunId: runId, asset: a } })}
              >
                {t('assets.actions.view_asset') || 'View'}
              </Button>
              {a.source_uri ? (
                <Button size="small" icon={<CopyOutlined />} onClick={() => copy(a.source_uri!)}>
                  {t('assets.actions.copy_source') || 'Source'}
                </Button>
              ) : null}
              {a.archive_path ? (
                <Button size="small" icon={<CopyOutlined />} onClick={() => copy(a.archive_path!)}>
                  {t('assets.actions.copy_archive') || 'Archive'}
                </Button>
              ) : null}
              <Button size="small" icon={<DownloadOutlined />} disabled={!href} onClick={() => href && window.open(href, '_blank')}>
                {t('download') || 'Download'}
              </Button>
            </Space>
          }
        />

        {a.kind === 'config' && a.meta ? (
          <Space direction="vertical" style={{ width: '100%' }} size={6}>
            {a.meta?.args ? (
              <div>
                <Text type="secondary">{t('assets.config.args') || 'args'}</Text>
                <pre style={{ margin: 0, maxHeight: 240, overflow: 'auto' }}>{JSON.stringify(a.meta.args, null, 2)}</pre>
              </div>
            ) : null}
            {Array.isArray(a.meta?.config_files) && a.meta.config_files.length > 0 ? (
              <div>
                <Text type="secondary">{t('assets.config.config_files') || 'config_files'}</Text>
                <pre style={{ margin: 0, maxHeight: 200, overflow: 'auto' }}>{JSON.stringify(a.meta.config_files, null, 2)}</pre>
              </div>
            ) : null}
          </Space>
        ) : null}
      </Card>
    )
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (parsed.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('assets.empty.no_assets') || 'No assets'} />
  }

  return (
    <Collapse
      defaultActiveKey={['code', 'config', 'dataset', 'pretrained', 'output']}
      items={[
        {
          key: 'code',
          label: (
            <Space>
              <CodeOutlined />
              <span>{t('assets.table.code') || 'Code'}</span>
              <Tag>{groups.code.length}</Tag>
            </Space>
          ),
          children: groups.code.length ? groups.code.map(renderAssetRow) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('assets.empty.no_assets') || 'No assets'} />, 
        },
        {
          key: 'config',
          label: (
            <Space>
              <SettingOutlined />
              <span>{t('assets.table.config') || 'Config'}</span>
              <Tag>{groups.config.length}</Tag>
            </Space>
          ),
          children: groups.config.length ? groups.config.map(renderAssetRow) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('assets.empty.no_assets') || 'No assets'} />,
        },
        {
          key: 'dataset',
          label: (
            <Space>
              <DatabaseOutlined />
              <span>{t('assets.table.datasets') || 'Datasets'}</span>
              <Tag>{groups.dataset.length}</Tag>
            </Space>
          ),
          children: groups.dataset.length ? groups.dataset.map(renderAssetRow) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('assets.empty.no_assets') || 'No assets'} />,
        },
        {
          key: 'pretrained',
          label: (
            <Space>
              <RocketOutlined />
              <span>{t('assets.table.pretrained') || 'Pretrained'}</span>
              <Tag>{groups.pretrained.length}</Tag>
            </Space>
          ),
          children: groups.pretrained.length ? groups.pretrained.map(renderAssetRow) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('assets.empty.no_assets') || 'No assets'} />,
        },
        {
          key: 'output',
          label: (
            <Space>
              <Tag>{t('assets.kind.output') || 'output'}</Tag>
              <span>{t('assets.table.outputs') || 'Outputs'}</span>
              <Tag>{groups.output.length}</Tag>
            </Space>
          ),
          children: groups.output.length ? groups.output.map(renderAssetRow) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('assets.empty.no_assets') || 'No assets'} />,
        },
      ]}
    />
  )
}

function RowLine(props: { left: React.ReactNode; right: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 6 }}>
      <div style={{ minWidth: 0 }}>{props.left}</div>
      <div style={{ flexShrink: 0 }}>{props.right}</div>
    </div>
  )
}
