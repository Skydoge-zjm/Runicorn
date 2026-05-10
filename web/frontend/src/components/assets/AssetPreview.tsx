import { lazy, Suspense, useMemo } from 'react'
import { Alert, Skeleton, Space, Typography, theme } from 'antd'
import { useTranslation } from 'react-i18next'
import { isProbablyTextFilename, suggestAssetDownloadFilename } from '../../utils/assetDownload'

const { Text } = Typography
const CodeArchivePreview = lazy(() => import('./code/CodeArchivePreview'))
const TextFilePreview = lazy(() => import('./TextFilePreview'))

function AssetPreviewFallback() {
  return <Skeleton active paragraph={{ rows: 6 }} />
}

export default function AssetPreview(props: { runId?: string; asset: any; archivePath?: string }) {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const kind = String(props.asset?.kind || '')

  const configText = useMemo(() => {
    if (kind !== 'config') return null
    const meta = props.asset?.meta
    if (!meta) return null
    try {
      return JSON.stringify(meta, null, 2)
    } catch {
      return String(meta)
    }
  }, [kind, props.asset?.meta])

  if (kind === 'config') {
    return (
      <pre style={{ margin: 0, maxHeight: 520, overflow: 'auto', background: token.colorBgLayout, color: token.colorText, padding: 12, borderRadius: 6, border: `1px solid ${token.colorBorderSecondary}` }}>
        {configText || '-'}
      </pre>
    )
  }

  if (!props.archivePath) {
    return <Text type="secondary">{t('assets.preview.no_archive')}</Text>
  }

  if (kind === 'code') {
    return (
      <Suspense fallback={<AssetPreviewFallback />}>
        <CodeArchivePreview runId={props.runId} archivePath={props.archivePath} />
      </Suspense>
    )
  }

  const filename = suggestAssetDownloadFilename(props.asset)
  if (isProbablyTextFilename(filename)) {
    return (
      <Suspense fallback={<AssetPreviewFallback />}>
        <TextFilePreview runId={props.runId} archivePath={props.archivePath} filename={filename} />
      </Suspense>
    )
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        message={t('assets.preview.no_inline')}
        description={t('assets.preview.not_previewable')}
      />
      <Text type="secondary">{t('assets.preview.try_download')}</Text>
    </Space>
  )
}
