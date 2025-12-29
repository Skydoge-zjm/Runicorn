import React, { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Space, Tag, Typography, Table, message } from 'antd'
import { useTranslation } from 'react-i18next'
import { ArrowLeftOutlined, DownloadOutlined } from '@ant-design/icons'
import { decodeAssetIdentity } from '../utils/assetIdentity'
import { loadAssetsIndexFromCache, AssetsIndexRepoRow } from '../hooks/useAssetsIndex'
import { downloadRunAssetUrl, getRunAssets } from '../api'
import { parseRunAssetsPayload } from '../utils/assetParse'
import { assetIdentityToString } from '../utils/assetIdentity'
import AssetPreview from '../components/assets/AssetPreview'
import { suggestAssetDownloadFilename } from '../utils/assetDownload'
import { formatRelativeTime } from '../utils/format'

const { Text, Title } = Typography

export default function AssetDetailPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { id = '' } = useParams()
  const location = useLocation()

  const [repoRow, setRepoRow] = useState<AssetsIndexRepoRow | null>(null)
  const [loading, setLoading] = useState(false)
  const [previewAsset, setPreviewAsset] = useState<any | null>(null)

  const identity = useMemo(() => decodeAssetIdentity(id), [id])

  const navState = (location.state || {}) as any
  const fromRunId = typeof navState?.fromRunId === 'string' ? navState.fromRunId : undefined
  const fromAsset = navState?.asset

  useEffect(() => {
    if (!identity) {
      setRepoRow(null)
      return
    }

    const key = assetIdentityToString(identity)
    if (fromAsset && fromAsset.identity) {
      try {
        const fromKey = assetIdentityToString(fromAsset.identity)
        if (fromKey === key) {
          const cache = loadAssetsIndexFromCache()
          const runProject = fromRunId ? cache?.runs?.find((r) => r.run_id === fromRunId)?.project : undefined
          setRepoRow({
            key,
            encoded: id,
            identity,
            kind: fromAsset.kind,
            name: fromAsset.name,
            saved: Boolean(fromAsset.saved),
            fingerprint: fromAsset.fingerprint,
            archive_path: fromAsset.archive_path,
            source_uri: fromAsset.source_uri,
            description: fromAsset.description,
            context: fromAsset.context,
            source_type: fromAsset.source_type,
            projects: runProject ? [runProject] : [],
            runs_count: fromRunId ? 1 : 0,
            run_ids: fromRunId ? [fromRunId] : [],
            last_used_time: undefined,
          })
          setPreviewAsset(fromAsset)
          return
        }
      } catch {
      }
    }

    const cache = loadAssetsIndexFromCache()
    const found = cache?.repo?.find((r) => r.key === key) || null
    setRepoRow(found)

    if (found && cache && !previewAsset) {
      const runIds = found.run_ids || []
      for (const rid of runIds) {
        const assets = cache.run_assets?.[rid] || []
        const hit = assets.find((a) => assetIdentityToString(a.identity) === key)
        if (hit) {
          setPreviewAsset(hit)
          break
        }
      }
    }
  }, [identity, id, fromAsset, fromRunId, previewAsset])

  const runRows = useMemo(() => {
    const runIds = repoRow?.run_ids || []
    return runIds.map((rid) => ({ run_id: rid }))
  }, [repoRow?.run_ids])

  const handleDownload = async (runId: string) => {
    if (!repoRow?.archive_path) return
    const href = downloadRunAssetUrl(runId, repoRow.archive_path, suggestAssetDownloadFilename(repoRow))
    window.open(href, '_blank')
  }

  const ensureInSync = async () => {
    if (!identity) return
    if (repoRow) return

    const cache = loadAssetsIndexFromCache()
    if (!cache) return

    const key = assetIdentityToString(identity)

    setLoading(true)
    try {
      const runIds = cache.runs.map((r) => r.run_id)
      for (const rid of runIds) {
        const payload = await getRunAssets(rid)
        const parsed = parseRunAssetsPayload(payload)
        const hit = parsed.find((a) => assetIdentityToString(a.identity) === key)
        if (hit) {
          const runProject = cache?.runs?.find((r) => r.run_id === rid)?.project
          setRepoRow({
            key,
            encoded: id,
            identity,
            kind: hit.kind,
            name: hit.name,
            saved: Boolean(hit.saved),
            fingerprint: hit.fingerprint,
            archive_path: hit.archive_path,
            source_uri: hit.source_uri,
            description: hit.description,
            context: hit.context,
            source_type: hit.source_type,
            projects: runProject ? [runProject] : [],
            runs_count: 1,
            run_ids: [rid],
            last_used_time: undefined,
          })
          setPreviewAsset(hit)
          return
        }
      }
    } catch (e: any) {
      message.error(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    ensureInSync()
  }, [id])

  if (!identity) {
    return (
      <Card>
        <Space direction="vertical">
          <Title level={4}>{t('asset_detail.title') || 'Asset Detail'}</Title>
          <Text type="secondary">{t('asset_detail.invalid_id') || 'Invalid asset id'}</Text>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/assets')}>{t('asset_detail.back') || 'Back'}</Button>
        </Space>
      </Card>
    )
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space wrap>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/assets')}>{t('asset_detail.back') || 'Back'}</Button>
            <Title level={4} style={{ margin: 0 }}>{t('asset_detail.title') || 'Asset Detail'}</Title>
          </Space>

          {!repoRow ? (
            <Text type="secondary">
              {loading
                ? (t('asset_detail.loading') || 'Loading...')
                : (t('asset_detail.not_found') || 'Not found in local index. Please refresh index on Assets page.')}
            </Text>
          ) : (
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space wrap>
                <Tag>{repoRow.kind}</Tag>
                {repoRow.saved ? (
                  <Tag color="green">{t('assets.tag.saved') || 'saved'}</Tag>
                ) : (
                  <Tag>{t('assets.tag.ref') || 'ref'}</Tag>
                )}
                <Text strong>{repoRow.name}</Text>
              </Space>

              {Array.isArray(repoRow.projects) && repoRow.projects.length > 0 ? (
                <div>
                  <Text type="secondary">{t('asset_detail.fields.projects') || 'Projects'}: </Text>
                  <Space wrap>
                    {repoRow.projects.map((p) => (
                      <Tag key={p}>{p}</Tag>
                    ))}
                  </Space>
                </div>
              ) : null}

              {repoRow.last_used_time ? (
                <div>
                  <Text type="secondary">{t('asset_detail.fields.last_used') || 'Last used'}: </Text>
                  <Text>{formatRelativeTime(repoRow.last_used_time)}</Text>
                </div>
              ) : null}

              {repoRow.description ? (
                <div>
                  <Text type="secondary">{t('asset_detail.fields.description') || 'Description'}: </Text>
                  <Text>{repoRow.description}</Text>
                </div>
              ) : null}

              {repoRow.context ? (
                <div>
                  <Text type="secondary">{t('asset_detail.fields.context') || 'Context'}: </Text>
                  <Tag>{repoRow.context}</Tag>
                </div>
              ) : null}

              {repoRow.source_type ? (
                <div>
                  <Text type="secondary">{t('asset_detail.fields.source_type') || 'Source Type'}: </Text>
                  <Tag>{repoRow.source_type}</Tag>
                </div>
              ) : null}

              <div>
                <Text type="secondary">{t('asset_detail.fields.source') || 'Source'}: </Text>
                <Text code>{repoRow.source_uri || '-'}</Text>
              </div>

              <div>
                <Text type="secondary">{t('asset_detail.fields.archive') || 'Archive'}: </Text>
                <Text code>{repoRow.archive_path || '-'}</Text>
              </div>

              <div>
                <Text type="secondary">{t('asset_detail.fields.fingerprint') || 'Fingerprint'}: </Text>
                <Text code>{repoRow.fingerprint || '-'}</Text>
              </div>
            </Space>
          )}
        </Space>
      </Card>

      <Card title={t('asset_detail.preview') || 'Preview'}>
        {repoRow?.kind ? (
          <AssetPreview
            runId={fromRunId || repoRow.run_ids?.[0]}
            asset={previewAsset || repoRow}
            archivePath={repoRow.archive_path}
          />
        ) : (
          <Text type="secondary">-</Text>
        )}
      </Card>

      <Card title={t('asset_detail.used_by') || 'Used By Runs'}>
        <Table
          dataSource={runRows}
          rowKey={(r: any) => r.run_id}
          size="small"
          pagination={{ pageSize: 10 }}
          columns={[
            {
              title: 'Run ID',
              dataIndex: 'run_id',
              key: 'run_id',
              render: (rid: string) => (
                <Button type="link" onClick={() => navigate(`/runs/${rid}`)}>
                  {rid}
                </Button>
              ),
            },
            {
              title: t('assets.repo.actions') || 'Actions',
              key: 'actions',
              width: 160,
              render: (_: any, r: any) => (
                <Space>
                  <Button size="small" onClick={() => navigate(`/runs/${r.run_id}`)}>{t('assets.actions.open_run') || 'Open Run'}</Button>
                  <Button
                    size="small"
                    icon={<DownloadOutlined />}
                    disabled={!repoRow?.archive_path}
                    onClick={() => handleDownload(r.run_id)}
                  >
                    {t('download') || 'Download'}
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </Space>
  )
}
