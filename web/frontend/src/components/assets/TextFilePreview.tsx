import React, { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Space, Spin, Typography } from 'antd'
import { useTranslation } from 'react-i18next'
import { downloadRunAssetUrl } from '../../api'

const { Text } = Typography

export default function TextFilePreview(props: { runId?: string; archivePath: string; filename?: string }) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [text, setText] = useState<string>('')

  const href = useMemo(() => {
    if (!props.runId) return null
    return downloadRunAssetUrl(props.runId, props.archivePath, props.filename)
  }, [props.runId, props.archivePath, props.filename])

  useEffect(() => {
    if (!href) return

    let cancelled = false
    setLoading(true)
    setError(null)

    fetch(href)
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text())
        return res.text()
      })
      .then((t) => {
        if (cancelled) return
        setText(t)
      })
      .catch((e: any) => {
        if (cancelled) return
        setError(String(e))
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [href])

  if (!props.runId) {
    return <Text type="secondary">{t('assets.preview.no_run_id') || 'No run id to fetch preview.'}</Text>
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Space wrap>
        {href ? (
          <Button size="small" onClick={() => window.open(href, '_blank')}>
            {t('assets.preview.open_download') || 'Open / Download'}
          </Button>
        ) : null}
        {props.filename ? <Text type="secondary">{props.filename}</Text> : null}
      </Space>

      {loading ? (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Spin />
        </div>
      ) : error ? (
        <Alert type="error" showIcon message={t('assets.preview.failed_to_load') || 'Failed to load preview'} description={error} />
      ) : (
        <pre style={{ margin: 0, maxHeight: 520, overflow: 'auto' }}>{text || '-'}</pre>
      )}
    </Space>
  )
}
