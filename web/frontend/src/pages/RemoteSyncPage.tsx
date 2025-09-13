import React, { useEffect, useState } from 'react'
import { Button, Divider, Input, Space, Typography, message } from 'antd'
import { sshConnect, sshClose, sshListdir, sshMirrorStart, sshMirrorStop, sshMirrorList } from '../api'

export default function RemoteSyncPage() {
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
    if (!sshHost || !sshUser) { message.warning('请填写主机与用户名'); return }
    try {
      setSshConnecting(true)
      const res = await sshConnect({ host: sshHost.trim(), port: sshPort || 22, username: sshUser.trim(), password: sshPassword || undefined, pkey: sshPkey || undefined, pkey_path: sshPkeyPath || undefined })
      setSshSessionId(res.session_id)
      message.success('SSH 已连接')
      setSshRemotePath('~')
      await listRemote('~', res.session_id)
    } catch (e: any) {
      message.error(typeof e?.message === 'string' ? e.message : '连接失败')
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
      message.error(typeof e?.message === 'string' ? e.message : '读取目录失败')
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
    if (!sshSessionId) { message.warning('请先建立 SSH 连接'); return }
    if (!sshRemotePath) { message.warning('请选择远程目录'); return }
    try {
      await sshMirrorStart({ session_id: sshSessionId, remote_root: sshRemotePath, interval: mirrorIntervalSec })
      message.success('已启动实时同步')
      await loadMirrorList()
      // notify runs page to refresh
      try { window.dispatchEvent(new Event('runicorn:refresh')) } catch {}
    } catch (e: any) {
      message.error(typeof e?.message === 'string' ? e.message : '启动失败')
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
      <Typography.Title level={3}>远程同步（SSH）</Typography.Title>
      <Typography.Paragraph type="secondary">
        建立到 Linux 服务器的 SSH 连接，浏览并选择远程目录作为数据源，实时同步到本地 storage 并在“Runs”页面可视化。
      </Typography.Paragraph>

      <Divider />

      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Typography.Title level={5}>连接到服务器</Typography.Title>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space wrap>
              <Input style={{ width: 180 }} placeholder="主机，例如 10.0.0.2" value={sshHost} onChange={e => setSshHost(e.target.value)} />
              <Input style={{ width: 90 }} placeholder="端口" value={sshPort} onChange={e => setSshPort(Number(e.target.value)||22)} />
              <Input style={{ width: 140 }} placeholder="用户名" value={sshUser} onChange={e => setSshUser(e.target.value)} />
              <Input.Password style={{ width: 180 }} placeholder="密码（可选）" value={sshPassword} onChange={e => setSshPassword(e.target.value)} />
            </Space>
            <Space wrap>
              <Input style={{ width: 360 }} placeholder="私钥内容（可选）" value={sshPkey} onChange={e => setSshPkey(e.target.value)} />
              <Input style={{ width: 260 }} placeholder="或 私钥路径（可选，如 ~/.ssh/id_rsa）" value={sshPkeyPath} onChange={e => setSshPkeyPath(e.target.value)} />
            </Space>
            <Space>
              {!sshSessionId ? (
                <Button type="primary" loading={sshConnecting} onClick={doSshConnect}>连接</Button>
              ) : (
                <>
                  <Typography.Text type="secondary">已连接：{sshUser}@{sshHost}:{sshPort}</Typography.Text>
                  <Button danger onClick={doSshClose}>断开</Button>
                </>
              )}
            </Space>
          </Space>
        </div>

        {sshSessionId && (
          <div>
            <Typography.Title level={5}>选择远程目录</Typography.Title>
            <Space align="center" style={{ marginBottom: 8 }}>
              <Typography.Text>当前目录：</Typography.Text>
              <Typography.Text code>{sshRemotePath}</Typography.Text>
              <Button size="small" onClick={pathUp}>上一级</Button>
              <Button size="small" loading={sshListing} onClick={() => listRemote(sshRemotePath)}>刷新</Button>
            </Space>
            <div style={{ maxHeight: 260, overflow: 'auto', border: '1px solid #eee', borderRadius: 6, padding: 8 }}>
              {sshItems.map(it => (
                <div key={it.path} style={{ cursor: it.type==='dir' ? 'pointer' : 'default', padding: '2px 4px' }}
                     onClick={() => it.type==='dir' && listRemote(it.path)}>
                  <span style={{ color: it.type==='dir' ? '#1677ff' : '#999' }}>{it.type === 'dir' ? '📁' : '📄'}</span>
                  <span style={{ marginLeft: 8 }}>{it.name}</span>
                </div>
              ))}
              {sshItems.length === 0 && <div style={{ color: '#999' }}>空目录或无权限</div>}
            </div>
            <Space style={{ marginTop: 8 }}>
              <Input style={{ width: 380 }} value={sshRemotePath} onChange={e => setSshRemotePath(e.target.value)} />
              <Input style={{ width: 120 }} value={mirrorIntervalSec} onChange={e => setMirrorIntervalSec(Number(e.target.value)||2)} suffix="秒" />
              <Button type="primary" onClick={startMirror}>同步此目录</Button>
            </Space>
            <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>
              建议选择到 <code>project/name/runs</code>（新结构）或 <code>runs</code>（旧结构）这一层而不是具体 <code>&lt;run_id&gt;</code>。
            </Typography.Paragraph>
          </div>
        )}

        <Divider />

        <div>
          <Typography.Title level={5} style={{ marginBottom: 8 }}>同步任务</Typography.Title>
          <div style={{ border: '1px solid #eee', borderRadius: 6, padding: 8 }}>
            {mirrorList.map(m => (
              <div key={m.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 0' }}>
                <div>
                  <div><b>{m.remote_root}</b> ➜ <code>{m.local_root}</code></div>
                  <div style={{ color: '#999', fontSize: 12 }}>copied: {m.stats?.copied_files ?? 0}, appended: {m.stats?.appended_bytes ?? 0}B, scans: {m.stats?.scans ?? 0}, alive: {String(m.alive)}</div>
                </div>
                <Button danger size="small" onClick={() => stopMirror(m.id)}>停止</Button>
              </div>
            ))}
            {mirrorList.length === 0 && <div style={{ color: '#999' }}>暂无任务</div>}
          </div>
        </div>

        <div>
          <Typography.Paragraph>
            同步成功后，前往 <a href="/runs">Runs</a> 页面查看实时可视化。
          </Typography.Paragraph>
        </div>
      </Space>
    </div>
  )
}
