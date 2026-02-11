import React, { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Space, Spin, Tree, Typography } from 'antd'
import { FileTextOutlined, FolderOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import JSZip from 'jszip'
import { downloadRunAssetUrl } from '../../../api'
import { isProbablyTextFilename } from '../../../utils/assetDownload'
import CodeTextViewer from './CodeTextViewer'

const { Text } = Typography

type TreeNode = {
  key: string
  title: string
  children?: TreeNode[]
  isLeaf?: boolean
  selectable?: boolean
  icon?: React.ReactNode
}

function isProbablyTextBytes(bytes: Uint8Array): boolean {
  if (!bytes.length) return true

  const sample = bytes.subarray(0, Math.min(bytes.length, 4096))
  for (let i = 0; i < sample.length; i++) {
    if (sample[i] === 0) return false
  }

  let ctrl = 0
  for (let i = 0; i < sample.length; i++) {
    const b = sample[i]
    if (b < 7 || (b > 13 && b < 32)) ctrl++
  }
  if (ctrl / sample.length > 0.08) return false
  return true
}

function buildTree(paths: string[]): TreeNode[] {
  const root: any = { children: new Map<string, any>() }

  paths.forEach((p) => {
    const parts = p.split('/').filter(Boolean)
    let cur = root
    for (let i = 0; i < parts.length; i++) {
      const name = parts[i]
      if (!cur.children.has(name)) {
        cur.children.set(name, { name, children: new Map<string, any>() })
      }
      cur = cur.children.get(name)
    }
    cur.__file = true
  })

  function toNodes(node: any, prefix: string): TreeNode[] {
    const names = (Array.from(node.children.keys()) as string[]).sort((a: string, b: string) => a.localeCompare(b))
    return names.map((name) => {
      const child = node.children.get(name)
      const path = prefix ? `${prefix}/${name}` : name
      const hasChildren = child.children && child.children.size > 0
      const isLeaf = Boolean(child.__file) && !hasChildren
      return {
        key: path,
        title: name,
        isLeaf,
        selectable: isLeaf,
        icon: isLeaf ? <FileTextOutlined /> : <FolderOutlined />,
        children: hasChildren ? toNodes(child, path) : undefined,
      }
    })
  }

  return toNodes(root, '')
}

export default function CodeArchivePreview(props: { runId?: string; archivePath: string }) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [zip, setZip] = useState<JSZip | null>(null)
  const [tree, setTree] = useState<TreeNode[]>([])
  const [selectedPath, setSelectedPath] = useState<string>('')
  const [fileText, setFileText] = useState<string>('')
  const [fileError, setFileError] = useState<string | null>(null)

  const href = useMemo(() => {
    if (!props.runId) return null
    return downloadRunAssetUrl(props.runId, props.archivePath, 'code_snapshot.zip')
  }, [props.runId, props.archivePath])

  useEffect(() => {
    if (!href) return

    let cancelled = false
    setLoading(true)
    setError(null)
    setZip(null)
    setTree([])
    setSelectedPath('')
    setFileText('')
    setFileError(null)

    fetch(href)
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text())
        const cl = res.headers.get('content-length')
        if (cl) {
          const n = Number(cl)
          if (Number.isFinite(n) && n > 50 * 1024 * 1024) {
            throw new Error(t('assets.code_preview.zip_too_large') || 'Zip too large to preview in browser')
          }
        }
        const buf = await res.arrayBuffer()
        const z = await JSZip.loadAsync(buf)
        return z
      })
      .then((z) => {
        if (cancelled) return
        setZip(z)
        const files = Object.keys(z.files)
          .filter((k) => !z.files[k].dir)
          .filter((k) => k && !k.startsWith('__MACOSX/'))
        setTree(buildTree(files))
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

  const loadFile = async (path: string) => {
    if (!zip) return
    setSelectedPath(path)
    setFileText('')
    setFileError(null)

    const f = zip.file(path)
    if (!f) {
      setFileError(t('assets.code_preview.file_not_found') || 'File not found in zip')
      return
    }

    try {
      const bytes = await f.async('uint8array')
      const maybeTextByName = isProbablyTextFilename(path)
      const maybeText = maybeTextByName || isProbablyTextBytes(bytes)
      if (!maybeText) {
        setFileError(t('assets.code_preview.binary_or_unsupported') || 'Binary or unsupported file type')
        return
      }

      const content = new TextDecoder('utf-8', { fatal: false }).decode(bytes)
      if (content.length > 400_000) {
        setFileText(content.slice(0, 400_000))
        setFileError(t('assets.code_preview.truncated') || 'Truncated (file too large)')
        return
      }
      setFileText(content)
    } catch (e: any) {
      setFileError(String(e))
    }
  }

  if (!props.runId) {
    return <Text type="secondary">{t('assets.code_preview.no_run_id') || 'No run id to fetch code archive.'}</Text>
  }

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin />
      </div>
    )
  }

  if (error) {
    return <Alert type="error" showIcon message={t('assets.code_preview.failed_to_load') || 'Failed to load code archive'} description={error} />
  }

  return (
    <div style={{ display: 'flex', gap: 12, width: '100%', minHeight: 420 }}>
      <div style={{ width: 320, borderRight: '1px solid #f0f0f0', paddingRight: 12, overflow: 'auto' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space wrap>
            {href ? (
              <Button size="small" onClick={() => window.open(href, '_blank')}>
                {t('assets.code_preview.download_zip') || 'Download Zip'}
              </Button>
            ) : null}
          </Space>
          <Tree
            treeData={tree as any}
            showIcon
            expandAction="click"
            selectedKeys={selectedPath ? [selectedPath] : []}
            onSelect={(keys: any, info: any) => {
              const k = String(info?.node?.key || '')
              if (!info?.node?.isLeaf) return
              if (k) loadFile(k)
            }}
          />
        </Space>
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text type="secondary">{selectedPath || (t('assets.code_preview.select_file') || 'Select a file')}</Text>
          {fileError ? <Alert type="warning" showIcon message={fileError} /> : null}
          {selectedPath && !fileError ? (
            <CodeTextViewer value={fileText || ''} filename={selectedPath} maxHeight={520} />
          ) : (
            <pre style={{ margin: 0, maxHeight: 520, overflow: 'auto' }}>{''}</pre>
          )}
        </Space>
      </div>
    </div>
  )
}
