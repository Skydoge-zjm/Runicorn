import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Table, Tag, Space, Button, Switch, Tooltip } from 'antd'
import { Link } from 'react-router-dom'
import { listRuns } from '../api'

export default function RunsPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const rows = await listRuns()
      setData(rows)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!autoRefresh) return
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [autoRefresh, load])

  const columns = useMemo(() => ([
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
