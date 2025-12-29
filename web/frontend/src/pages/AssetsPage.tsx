import React, { useMemo, useState } from 'react'
import { Card, Row, Col, Statistic, Tabs, Table, Space, Button, Tag, Input, Select, Switch, Typography } from 'antd'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { ReloadOutlined, EyeOutlined } from '@ant-design/icons'
import { useAssetsIndex } from '../hooks/useAssetsIndex'
import { formatRelativeTime } from '../utils/format'

const { Text } = Typography

export default function AssetsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { index, loading, progress, stats, refresh } = useAssetsIndex()

  const [repoType, setRepoType] = useState<string>('all')
  const [onlyArchived, setOnlyArchived] = useState(false)
  const [onlyRelated, setOnlyRelated] = useState(true)
  const [projectFilter, setProjectFilter] = useState<string>('all')
  const [sortMode, setSortMode] = useState<'recent' | 'name'>('recent')
  const [repoSearch, setRepoSearch] = useState('')

  const projectOptions = useMemo(() => {
    const projects = Array.from(new Set((index?.runs || []).map((r) => String(r.project || 'default')))).sort()
    return [{ value: 'all', label: t('assets.filters.project') || 'Project' }, ...projects.map((p) => ({ value: p, label: p }))]
  }, [index?.runs, t])

  const repoRows = useMemo(() => {
    const rows = index?.repo || []
    const q = repoSearch.trim().toLowerCase()

    const filtered = rows.filter((r) => {
      if (repoType !== 'all' && r.kind !== repoType) return false
      if (onlyArchived && !r.saved) return false
      if (onlyRelated && (r.runs_count || 0) <= 0) return false
      if (projectFilter !== 'all' && !(r.projects || []).includes(projectFilter)) return false
      if (!q) return true
      const hay = `${r.name} ${r.kind} ${(r.projects || []).join(' ')} ${r.source_uri || ''} ${r.archive_path || ''} ${r.description || ''} ${r.context || ''} ${r.source_type || ''}`.toLowerCase()
      return hay.includes(q)
    })

    if (sortMode === 'name') {
      return filtered.slice().sort((a, b) => a.name.localeCompare(b.name))
    }
    return filtered.slice().sort((a, b) => {
      const ta = a.last_used_time || 0
      const tb = b.last_used_time || 0
      if (ta !== tb) return tb - ta
      return a.name.localeCompare(b.name)
    })
  }, [index?.repo, repoSearch, repoType, onlyArchived, onlyRelated, projectFilter, sortMode])

  const overviewRows = useMemo(() => index?.experiments || [], [index?.experiments])

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space direction="vertical" size={0}>
              <div style={{ fontSize: 18, fontWeight: 700 }}>{t('assets.title') || 'Assets'}</div>
              <Text type="secondary">{t('assets.subtitle') || ''}</Text>
            </Space>
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={() => refresh()} loading={loading}>
              {t('assets.actions.refresh_index') || 'Refresh Index'}
            </Button>
          </Col>
        </Row>

        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12} md={6}>
            <Statistic title={t('experiments.total_runs') || 'Total Runs'} value={stats.totalRuns} />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic title={t('assets.table.runs') || 'Runs'} value={stats.runsWithAssets} />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic title={t('assets.table.assets_total') || 'Assets'} value={stats.totalAssets} />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic title={t('assets.table.archived') || 'Archived'} value={stats.archivedAssets} />
          </Col>
        </Row>

        {loading && progress.total > 0 && (
          <div style={{ marginTop: 12 }}>
            <Text type="secondary">
              {t('assets.loading.index_progress', { done: progress.done, total: progress.total }) || `${progress.done}/${progress.total}`}
            </Text>
          </div>
        )}
      </Card>

      <Card>
        <Tabs
          items={[
            {
              key: 'overview',
              label: t('assets.tab.overview') || 'Overview',
              children: (
                <Table
                  dataSource={overviewRows}
                  rowKey={(r: any) => r.key}
                  size="middle"
                  pagination={{ pageSize: 20 }}
                  expandable={{
                    expandedRowRender: (r: any) => (
                      <Space wrap>
                        {(r.run_ids || []).map((rid: string) => (
                          <Button key={rid} size="small" type="link" onClick={() => navigate(`/runs/${rid}`)}>
                            {rid}
                          </Button>
                        ))}
                      </Space>
                    ),
                    rowExpandable: (r: any) => Array.isArray(r.run_ids) && r.run_ids.length > 0,
                  }}
                  columns={[
                    { title: t('assets.table.project') || 'Project', dataIndex: 'project', key: 'project', width: 180 },
                    { title: t('assets.table.name') || 'Experiment', dataIndex: 'name', key: 'name', width: 220 },
                    { title: t('assets.table.runs') || 'Runs', dataIndex: 'runs_count', key: 'runs_count', width: 100 },
                    { title: t('assets.table.assets_total') || 'Assets', dataIndex: 'assets_total', key: 'assets_total', width: 110 },
                    { title: t('assets.table.archived') || 'Archived', dataIndex: 'archived_total', key: 'archived_total', width: 110 },
                    {
                      title: t('assets.table.code') || 'Code',
                      key: 'code',
                      width: 90,
                      render: (_: any, r: any) => r.by_kind?.code || 0,
                    },
                    {
                      title: t('assets.table.config') || 'Config',
                      key: 'config',
                      width: 90,
                      render: (_: any, r: any) => r.by_kind?.config || 0,
                    },
                    {
                      title: t('assets.table.datasets') || 'Datasets',
                      key: 'dataset',
                      width: 100,
                      render: (_: any, r: any) => r.by_kind?.dataset || 0,
                    },
                    {
                      title: t('assets.table.pretrained') || 'Pretrained',
                      key: 'pretrained',
                      width: 110,
                      render: (_: any, r: any) => r.by_kind?.pretrained || 0,
                    },
                    {
                      title: t('assets.table.outputs') || 'Outputs',
                      key: 'output',
                      width: 100,
                      render: (_: any, r: any) => r.by_kind?.output || 0,
                    },
                  ]}
                />
              ),
            },
            {
              key: 'repo',
              label: t('assets.tab.repository') || 'Repository',
              children: (
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                  <Row gutter={12} align="middle">
                    <Col flex="220px">
                      <Select
                        value={repoType}
                        onChange={(v) => setRepoType(v)}
                        style={{ width: '100%' }}
                        options={[
                          { value: 'all', label: t('assets.filters.type') || 'Type' },
                          { value: 'code', label: 'code' },
                          { value: 'config', label: 'config' },
                          { value: 'dataset', label: 'dataset' },
                          { value: 'pretrained', label: 'pretrained' },
                          { value: 'output', label: 'output' },
                        ]}
                      />
                    </Col>
                    <Col flex="220px">
                      <Select value={projectFilter} onChange={setProjectFilter} style={{ width: '100%' }} options={projectOptions} />
                    </Col>
                    <Col flex="auto">
                      <Input
                        value={repoSearch}
                        onChange={(e) => setRepoSearch(e.target.value)}
                        placeholder={t('assets.filters.search') || 'Search'}
                      />
                    </Col>
                    <Col>
                      <Space>
                        <span>{t('assets.filters.only_archived') || 'Archived only'}</span>
                        <Switch checked={onlyArchived} onChange={setOnlyArchived} />
                      </Space>
                    </Col>
                    <Col>
                      <Space>
                        <span>{t('assets.filters.only_related') || 'Only related runs'}</span>
                        <Switch checked={onlyRelated} onChange={setOnlyRelated} />
                      </Space>
                    </Col>
                    <Col flex="220px">
                      <Select
                        value={sortMode}
                        onChange={(v) => setSortMode(v)}
                        style={{ width: '100%' }}
                        options={[
                          { value: 'recent', label: t('assets.filters.sort_recent') || 'Sort: Recent' },
                          { value: 'name', label: t('assets.filters.sort_name') || 'Sort: Name' },
                        ]}
                      />
                    </Col>
                  </Row>

                  <Table
                    dataSource={repoRows}
                    rowKey={(r: any) => r.key}
                    size="middle"
                    pagination={{ pageSize: 20 }}
                    columns={[
                      {
                        title: t('assets.repo.kind') || 'Type',
                        dataIndex: 'kind',
                        key: 'kind',
                        width: 120,
                        render: (v: string) => <Tag>{v}</Tag>,
                      },
                      {
                        title: t('assets.repo.asset') || 'Asset',
                        dataIndex: 'name',
                        key: 'name',
                        width: 220,
                        render: (v: string, r: any) => (
                          <Space direction="vertical" size={0} style={{ maxWidth: 260 }}>
                            <Text ellipsis title={v} strong>
                              {v}
                            </Text>
                            {Array.isArray(r.projects) && r.projects.length > 0 ? (
                              <Space wrap size={4}>
                                {r.projects.slice(0, 3).map((p: string) => (
                                  <Tag key={p}>{p}</Tag>
                                ))}
                                {r.projects.length > 3 ? <Tag>+{r.projects.length - 3}</Tag> : null}
                              </Space>
                            ) : null}
                          </Space>
                        ),
                      },
                      {
                        title: t('assets.repo.saved') || 'Archived',
                        dataIndex: 'saved',
                        key: 'saved',
                        width: 110,
                        render: (v: boolean) => (v ? <Tag color="green">saved</Tag> : <Tag>ref</Tag>),
                      },
                      {
                        title: t('assets.repo.last_used') || 'Last Used',
                        dataIndex: 'last_used_time',
                        key: 'last_used_time',
                        width: 140,
                        render: (v: number | undefined) => <Text type="secondary">{v ? formatRelativeTime(v) : '-'}</Text>,
                      },
                      {
                        title: t('assets.repo.description') || 'Description',
                        dataIndex: 'description',
                        key: 'description',
                        width: 220,
                        render: (v: string | undefined) => (v ? <Text ellipsis style={{ maxWidth: 240 }} title={v}>{v}</Text> : <span style={{ color: '#999' }}>-</span>),
                      },
                      {
                        title: t('assets.repo.context') || 'Context',
                        dataIndex: 'context',
                        key: 'context',
                        width: 120,
                        render: (v: string | undefined) => (v ? <Tag>{v}</Tag> : <span style={{ color: '#999' }}>-</span>),
                      },
                      {
                        title: t('assets.repo.source_type') || 'Source Type',
                        dataIndex: 'source_type',
                        key: 'source_type',
                        width: 140,
                        render: (v: string | undefined) => (v ? <Tag>{v}</Tag> : <span style={{ color: '#999' }}>-</span>),
                      },
                      {
                        title: t('assets.repo.source') || 'Source',
                        dataIndex: 'source_uri',
                        key: 'source_uri',
                        render: (v: string | undefined) => (v ? <Text ellipsis style={{ maxWidth: 360 }} title={v}>{v}</Text> : <span style={{ color: '#999' }}>-</span>),
                      },
                      {
                        title: t('assets.repo.archive') || 'Archive Path',
                        dataIndex: 'archive_path',
                        key: 'archive_path',
                        render: (v: string | undefined) => (v ? <Text ellipsis style={{ maxWidth: 360 }} title={v}>{v}</Text> : <span style={{ color: '#999' }}>-</span>),
                      },
                      { title: t('assets.repo.runs_count') || 'Runs', dataIndex: 'runs_count', key: 'runs_count', width: 90 },
                      {
                        title: t('assets.repo.actions') || 'Actions',
                        key: 'actions',
                        width: 120,
                        render: (_: any, r: any) => (
                          <Button
                            type="link"
                            icon={<EyeOutlined />}
                            onClick={() => navigate(`/assets/${r.encoded}`)}
                          >
                            {t('assets.actions.view_asset') || 'View'}
                          </Button>
                        ),
                      },
                    ]}
                  />
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </Space>
  )
}
