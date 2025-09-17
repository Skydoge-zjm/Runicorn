import React, { useEffect, useState } from 'react'
import { Button, Divider, Input, Space, Typography, message } from 'antd'
import { sshConnect, sshClose, sshListdir, sshMirrorStart, sshMirrorStop, sshMirrorList } from '../api'
import { useTranslation } from 'react-i18next'

export default function RemoteSyncPage() {
  const { t } = useTranslation()
  // SSH connection states
  const [sshHost, setSshHost] = useState('')
  const [sshPort, setSshPort] = useState<number | undefined>(22)
  const [sshUser, setSshUser] = useState('')
  const [sshPassword, setSshPassword] = useState('')
  const [sshPkey, setSshPkey] = useState('')
  const [sshPkeyPath, setSshPkeyPath] = useState('')
  const [sshSessionId, setSshSessionId] = useState<string>('')
  const [sshConnecting, setSshConnecting] = useState(false)

  // Remote browsing states
  const [sshRemotePath, setSshRemotePath] = useState<string>('~')
  const [sshListing, setSshListing] = useState(false)
  const [sshItems, setSshItems] = useState<Array<{ name: string; path: string; type: 'dir'|'file'; size: number; mtime: number }>>([])

  // Mirror tasks
  const [mirrorList, setMirrorList] = useState<any[]>([])
  const [mirrorLoading, setMirrorLoading] = useState(false)
  const [mirrorIntervalSec, setMirrorIntervalSec] = useState<number>(2)

  const loadMirrorList = async () => {
    try {
      setMirrorLoading(true)
      const res = await sshMirrorList()
      setMirrorList(res.mirrors || [])
    } catch { /* noop */ }
    finally { setMirrorLoading(false) }
  }

  useEffect(() => {
    let timer: any
    loadMirrorList()
    timer = setInterval(loadMirrorList, 3000)
    return () => { if (timer) clearInterval(timer) }
  }, [])

  const doSshConnect = async () => {
    if (!sshHost || !sshUser) { message.warning(t('remote.msg.fill_host_user')); return }
    try {
      setSshConnecting(true)
      const res = await sshConnect({ host: sshHost.trim(), port: sshPort || 22, username: sshUser.trim(), password: sshPassword || undefined, pkey: sshPkey || undefined, pkey_path: sshPkeyPath || undefined })
      setSshSessionId(res.session_id)
      message.success(t('remote.msg.ssh_connected'))
      setSshRemotePath('~')
      await listRemote('~', res.session_id)
    } catch (e: any) {
      message.error(typeof e?.message === 'string' ? e.message : t('remote.msg.connect_failed'))
    } finally { setSshConnecting(false) }
  }

  const doSshClose = async () => {
    if (!sshSessionId) return
    try {
      await sshClose(sshSessionId)
      setSshSessionId('')
      setSshItems([])
    } catch {}
  }

  const listRemote = async (path: string, sid?: string) => {
    if (!(sid || sshSessionId)) return
    try {
      setSshListing(true)
      const res = await sshListdir(sid || sshSessionId, path)
      setSshItems(res.items || [])
      setSshRemotePath(path)
    } catch (e: any) {
      message.error(typeof e?.message === 'string' ? e.message : t('remote.msg.dir_failed'))
    } finally { setSshListing(false) }
  }

  const pathUp = () => {
    try {
      const parts = sshRemotePath.split('/').filter(Boolean)
      if (sshRemotePath === '~') return
      if (sshRemotePath.startsWith('~')) {
        const rest = sshRemotePath.slice(1)
        const segs = rest.split('/').filter(Boolean)
        if (segs.length <= 1) { listRemote('~'); return }
        const parent = '~/' + segs.slice(0, -1).join('/')
        listRemote(parent)
        return
      }
      parts.pop()
      const parent = '/' + parts.join('/')
      listRemote(parent || '/')
    } catch {}
  }

  const startMirror = async () => {
    if (!sshSessionId) { message.warning(t('remote.msg.need_connect')); return }
    if (!sshRemotePath) { message.warning(t('remote.msg.need_path')); return }
    try {
      await sshMirrorStart({ session_id: sshSessionId, remote_root: sshRemotePath, interval: mirrorIntervalSec })
      message.success(t('remote.msg.started'))
      await loadMirrorList()
      // notify runs page to refresh
      try { window.dispatchEvent(new Event('runicorn:refresh')) } catch {}
    } catch (e: any) {
      message.error(typeof e?.message === 'string' ? e.message : t('remote.msg.start_failed'))
    }
  }

  const stopMirror = async (taskId: string) => {
    try {
      await sshMirrorStop(taskId)
      await loadMirrorList()
    } catch {}
  }

  return (
    <div>
      <Typography.Title level={3}>{t('remote.title')}</Typography.Title>
      <Typography.Paragraph type="secondary">
        {t('remote.desc')}
      </Typography.Paragraph>

      <Divider />

      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Typography.Title level={5}>{t('remote.connect.title')}</Typography.Title>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space wrap>
              <Input style={{ width: 180 }} placeholder={t('remote.placeholder.host')} value={sshHost} onChange={e => setSshHost(e.target.value)} />
              <Input style={{ width: 90 }} placeholder={t('remote.placeholder.port')} value={sshPort} onChange={e => setSshPort(Number(e.target.value)||22)} />
              <Input style={{ width: 140 }} placeholder={t('remote.placeholder.user')} value={sshUser} onChange={e => setSshUser(e.target.value)} />
              <Input.Password style={{ width: 180 }} placeholder={t('remote.placeholder.password')} value={sshPassword} onChange={e => setSshPassword(e.target.value)} />
            </Space>
            <Space wrap>
              <Input style={{ width: 360 }} placeholder={t('remote.placeholder.pkey')} value={sshPkey} onChange={e => setSshPkey(e.target.value)} />
              <Input style={{ width: 260 }} placeholder={t('remote.placeholder.pkey_path')} value={sshPkeyPath} onChange={e => setSshPkeyPath(e.target.value)} />
            </Space>
            <Space>
              {!sshSessionId ? (
                <Button type="primary" loading={sshConnecting} onClick={doSshConnect}>{t('remote.connect.button')}</Button>
              ) : (
                <>
                  <Typography.Text type="secondary">{t('remote.connected', { user: sshUser, host: sshHost, port: sshPort })}</Typography.Text>
                  <Button danger onClick={doSshClose}>{t('remote.disconnect')}</Button>
                </>
              )}
            </Space>
          </Space>
        </div>

        {sshSessionId && (
          <div>
            <Typography.Title level={5}>{t('remote.choose.title')}</Typography.Title>
            <Space align="center" style={{ marginBottom: 8 }}>
              <Typography.Text>{t('remote.current_dir')}</Typography.Text>
              <Typography.Text code>{sshRemotePath}</Typography.Text>
              <Button size="small" onClick={pathUp}>{t('remote.up')}</Button>
              <Button size="small" loading={sshListing} onClick={() => listRemote(sshRemotePath)}>{t('remote.refresh')}</Button>
            </Space>
            <div style={{ maxHeight: 260, overflow: 'auto', border: '1px solid #eee', borderRadius: 6, padding: 8 }}>
              {sshItems.map(it => (
                <div key={it.path} style={{ cursor: it.type==='dir' ? 'pointer' : 'default', padding: '2px 4px' }}
                     onClick={() => it.type==='dir' && listRemote(it.path)}>
                  <span style={{ color: it.type==='dir' ? '#1677ff' : '#999' }}>{it.type === 'dir' ? '📁' : '📄'}</span>
                  <span style={{ marginLeft: 8 }}>{it.name}</span>
                </div>
              ))}
              {sshItems.length === 0 && <div style={{ color: '#999' }}>{t('remote.empty')}</div>}
            </div>
            <Space style={{ marginTop: 8 }}>
              <Input style={{ width: 380 }} value={sshRemotePath} onChange={e => setSshRemotePath(e.target.value)} />
              <Input style={{ width: 120 }} value={mirrorIntervalSec} onChange={e => setMirrorIntervalSec(Number(e.target.value)||2)} suffix={t('remote.interval.suffix')} />
              <Button type="primary" onClick={startMirror}>{t('remote.sync_dir')}</Button>
            </Space>
            <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>
              {t('remote.tip')}
            </Typography.Paragraph>
          </div>
        )}

        <Divider />

        <div>
          <Typography.Title level={5} style={{ marginBottom: 8 }}>{t('remote.tasks.title')}</Typography.Title>
          <div style={{ border: '1px solid #eee', borderRadius: 6, padding: 8 }}>
            {mirrorList.map(m => (
              <div key={m.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 0' }}>
                <div>
                  <div><b>{m.remote_root}</b> ➜ <code>{m.local_root}</code></div>
                  <div style={{ color: '#999', fontSize: 12 }}>{t('remote.tasks.item.stats', {
                    copied: m.stats?.copied_files ?? 0,
                    appended: m.stats?.appended_bytes ?? 0,
                    scans: m.stats?.scans ?? 0,
                    alive: String(m.alive),
                  })}</div>
                </div>
                <Button danger size="small" onClick={() => stopMirror(m.id)}>{t('remote.tasks.stop')}</Button>
              </div>
            ))}
            {mirrorList.length === 0 && <div style={{ color: '#999' }}>{t('remote.tasks.none')}</div>}
          </div>
        </div>

        <div>
          <Typography.Paragraph>
            {t('remote.to_runs')}
          </Typography.Paragraph>
        </div>
      </Space>
    </div>
  )
}
