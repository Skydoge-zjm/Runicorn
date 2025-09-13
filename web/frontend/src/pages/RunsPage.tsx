import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Table, Tag, Space, Button, Switch, Tooltip, Select } from 'antd'
import { Link } from 'react-router-dom'
import { listRuns, listProjects, listNames, listRunsByName } from '../api'

export default function RunsPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [projects, setProjects] = useState<string[]>([])
  const [names, setNames] = useState<string[]>([])
  const [project, setProject] = useState<string | undefined>(undefined)
  const [name, setName] = useState<string | undefined>(undefined)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      let rows: any[] = []
      if (project && name) {
        rows = await listRunsByName(project, name)
      } else {
        rows = await listRuns()
      }
      setData(rows)
    } finally {
      setLoading(false)
    }
  }, [project, name])

  useEffect(() => {
    load()
  }, [load])

  // Refresh immediately when other components request it
  useEffect(() => {
    const handler = () => load()
    window.addEventListener('runicorn:refresh', handler)
    return () => window.removeEventListener('runicorn:refresh', handler)
  }, [load])

  // load projects
  useEffect(() => {
    (async () => {
      try {
        const res = await listProjects()
        setProjects(res.projects || [])
      } catch {}
    })()
  }, [])

  // load names when project changes
  useEffect(() => {
    if (!project) { setNames([]); setName(undefined); return }
    (async () => {
      try {
        const res = await listNames(project)
        setNames(res.names || [])
      } catch { setNames([]) }
    })()
  }, [project])

  useEffect(() => {
    if (!autoRefresh) return
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [autoRefresh, load])

  const columns = useMemo(() => ([
    {
      title: 'Project',
      dataIndex: 'project',
      render: (v: string | undefined) => v || '-',
    },
    {
      title: 'Name',
      dataIndex: 'name',
      render: (v: string | undefined) => v || '-',
    },
    {
      title: 'Run ID',
      dataIndex: 'id',
      render: (v: string) => <Link to={`/runs/${v}`}>{v}</Link>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      render: (v: string) => (
        <Tag color={v === 'running' ? 'processing' : 'default'}>{v}</Tag>
      ),
    },
    {
      title: 'Best Top1',
      dataIndex: 'best_val_acc_top1',
      render: (v: number | null) => (v != null ? `${v.toFixed(2)}%` : '-')
    },
    {
      title: 'PID',
      dataIndex: 'pid',
    },
    {
      title: 'Created',
      dataIndex: 'created_time',
      render: (ts?: number) => ts ? new Date(ts * 1000).toLocaleString() : '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, row: any) => (
        <Space>
          <Link to={`/runs/${row.id}`}>
            <Button size="small">View</Button>
          </Link>
        </Space>
      )
    }
  ]), [load])

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Space>
        <Button onClick={load} loading={loading}>Refresh</Button>
        <Tooltip title="Auto refresh every 5s">
          <span>
            Auto Refresh <Switch checked={autoRefresh} onChange={setAutoRefresh} style={{ marginLeft: 8 }} />
          </span>
        </Tooltip>
        <span>
          Project:&nbsp;
          <Select
            allowClear
            placeholder="All"
            value={project}
            onChange={setProject as any}
            style={{ width: 180 }}
            options={projects.map(p => ({ label: p, value: p }))}
          />
        </span>
        <span>
          Name:&nbsp;
          <Select
            allowClear
            placeholder="All"
            value={name}
            onChange={setName as any}
            style={{ width: 200 }}
            options={names.map(n => ({ label: n, value: n }))}
            disabled={!project}
          />
        </span>
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={data}
        columns={columns as any}
        pagination={{ pageSize: 10 }}
      />
    </Space>
  )
}
