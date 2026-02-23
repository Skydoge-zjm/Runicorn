import { useMemo } from 'react'
import { Alert, Space, Typography } from 'antd'
import { useTranslation } from 'react-i18next'
import CodeArchivePreview from './code/CodeArchivePreview'
import TextFilePreview from './TextFilePreview'
import { isProbablyTextFilename, suggestAssetDownloadFilename } from '../../utils/assetDownload'

const { Text } = Typography

export default function AssetPreview(props: { runId?: string; asset: any; archivePath?: string }) {
  const { t } = useTranslation()
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
      <pre style={{ margin: 0, maxHeight: 520, overflow: 'auto' }}>
        {configText || '-'}
      </pre>
    )
  }

  if (!props.archivePath) {
    return <Text type="secondary">{t('assets.preview.no_archive')}</Text>
  }

  if (kind === 'code') {
    return <CodeArchivePreview runId={props.runId} archivePath={props.archivePath} />
  }

  const filename = suggestAssetDownloadFilename(props.asset)
  if (isProbablyTextFilename(filename)) {
    return <TextFilePreview runId={props.runId} archivePath={props.archivePath} filename={filename} />
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
