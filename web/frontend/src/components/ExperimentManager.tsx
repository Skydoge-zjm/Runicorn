import React, { useState, useEffect } from 'react'
import { 
  Card, Table, Tag, Button, Input, Select, Space, Modal, 
  message, Tooltip, Badge, Dropdown, Checkbox, DatePicker,
  Drawer, Descriptions, Tabs, Progress, Alert, Empty, Typography
} from 'antd'
import {
  SearchOutlined, DeleteOutlined, TagsOutlined, DownloadOutlined,
  ExportOutlined, EyeOutlined, PushpinOutlined, InboxOutlined,
  FilterOutlined, SyncOutlined, MoreOutlined, StarOutlined,
  ExperimentOutlined, FolderOpenOutlined, InfoCircleOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { ColumnsType } from 'antd/es/table'

interface Experiment {
  id: string
  project: string
  name: string
  tags: string[]
  description?: string
  created_at: number
  updated_at: number
  archived: boolean
  pinned: boolean
  status?: string
  metrics?: Record<string, number>
}

export default function ExperimentManager() {
  const { t } = useTranslation()
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedRows, setSelectedRows] = useState<string[]>([])
  const [filters, setFilters] = useState({
    project: '',
    tags: [] as string[],
    text: '',
    archived: false,
    dateRange: null as any
  })
  const [tagModalVisible, setTagModalVisible] = useState(false)
  const [selectedExp, setSelectedExp] = useState<Experiment | null>(null)
  const [newTags, setNewTags] = useState<string[]>([])
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false)
  const [allTags, setAllTags] = useState<string[]>([])
  const [allProjects, setAllProjects] = useState<string[]>([])

  // Fetch experiments
  const fetchExperiments = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filters.project) params.append('project', filters.project)
      if (filters.tags.length) params.append('tags', filters.tags.join(','))
      if (filters.text) params.append('text', filters.text)
      params.append('archived', filters.archived.toString())
      
      const res = await fetch(`/api/experiments/search?${params}`)
      const data = await res.json()
      setExperiments(data.experiments || [])
      
      // Extract unique tags and projects
      const tags = new Set<string>()
      const projects = new Set<string>()
      data.experiments?.forEach((exp: Experiment) => {
        exp.tags?.forEach(tag => tags.add(tag))
        projects.add(exp.project)
      })
      setAllTags(Array.from(tags))
      setAllProjects(Array.from(projects))
    } catch (err) {
      message.error(t('Failed to fetch experiments'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchExperiments()
  }, [filters])

  // Handle tag addition
  const handleAddTags = async () => {
    if (!selectedExp || newTags.length === 0) return
    
    try {
      const res = await fetch('/api/experiments/tag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: selectedExp.id,
          tags: newTags,
          append: true
        })
      })
      
      if (res.ok) {
        message.success(t('Tags added successfully'))
        setTagModalVisible(false)
        setNewTags([])
        fetchExperiments()
      } else {
        message.error(t('Failed to add tags'))
      }
    } catch (err) {
      message.error(t('Network error'))
    }
  }

  // Handle deletion
  const handleDelete = async (runIds: string[]) => {
    Modal.confirm({
      title: t('Delete Experiments'),
      content: t(`Are you sure you want to delete ${runIds.length} experiment(s)?`),
      okText: t('Delete'),
      okType: 'danger',
      onOk: async () => {
        try {
          const res = await fetch('/api/experiments/delete', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ run_ids: runIds })
          })
          
          if (res.ok) {
            message.success(t('Deleted successfully'))
            fetchExperiments()
            setSelectedRows([])
          } else {
            message.error(t('Failed to delete'))
          }
        } catch (err) {
          message.error(t('Network error'))
        }
      }
    })
  }

  // Export experiment data
  const handleExport = async (runId: string, format: 'csv' | 'excel' | 'markdown' | 'html') => {
    try {
      let endpoint = `/api/export/${runId}`
      if (format === 'csv') endpoint += '/csv'
      else if (format === 'markdown' || format === 'html') endpoint += `/report?format=${format}`
      
      const res = await fetch(endpoint)
      if (res.ok) {
        const blob = await res.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${runId}_${format === 'csv' ? 'metrics.csv' : 
                      format === 'excel' ? 'metrics.xlsx' : 
                      `report.${format}`}`
        a.click()
        window.URL.revokeObjectURL(url)
        message.success(t('Export successful'))
      } else {
        message.error(t('Export failed'))
      }
    } catch (err) {
      message.error(t('Network error'))
    }
  }

  // View environment info
  const handleViewEnvironment = async (runId: string) => {
    try {
      const res = await fetch(`/api/environment/${runId}`)
      const data = await res.json()
      
      if (data.available) {
        Modal.info({
          title: t('Environment Information'),
          width: 800,
          content: (
            <Tabs>
              <Tabs.TabPane tab={t('Python')} key="python">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="Python Version">{data.environment.python_version}</Descriptions.Item>
                  <Descriptions.Item label="Platform">{data.environment.platform}</Descriptions.Item>
                </Descriptions>
                {data.environment.pip_packages && (
                  <div style={{ marginTop: 16 }}>
                    <h4>{t('Pip Packages')} ({data.environment.pip_packages.length})</h4>
                    <pre style={{ maxHeight: 300, overflow: 'auto', fontSize: 12 }}>
                      {data.environment.pip_packages.join('\n')}
                    </pre>
                  </div>
                )}
              </Tabs.TabPane>
              
              {data.environment.git_info && (
                <Tabs.TabPane tab={t('Git')} key="git">
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="Branch">{data.environment.git_info.branch}</Descriptions.Item>
                    <Descriptions.Item label="Commit">{data.environment.git_info.commit}</Descriptions.Item>
                    <Descriptions.Item label="Has Changes">{data.environment.git_info.has_changes ? 'Yes' : 'No'}</Descriptions.Item>
                    {data.environment.git_info.remote && (
                      <Descriptions.Item label="Remote">{data.environment.git_info.remote}</Descriptions.Item>
                    )}
                  </Descriptions>
                </Tabs.TabPane>
              )}
              
              {data.environment.gpu_info && (
                <Tabs.TabPane tab={t('GPU')} key="gpu">
                  {data.environment.gpu_info.map((gpu: any, i: number) => (
                    <Card key={i} size="small" style={{ marginBottom: 8 }}>
                      <Descriptions column={2} size="small">
                        <Descriptions.Item label="GPU">{gpu.name}</Descriptions.Item>
                        <Descriptions.Item label="Memory">{gpu.memory_total_mb} MB</Descriptions.Item>
                      </Descriptions>
                    </Card>
                  ))}
                </Tabs.TabPane>
              )}
            </Tabs>
          )
        })
      } else {
        message.info(t('No environment information available'))
      }
    } catch (err) {
      message.error(t('Failed to fetch environment'))
    }
  }

  const columns: ColumnsType<Experiment> = [
    {
      title: '',
      key: 'select',
      width: 50,
      render: (_, record) => (
        <Checkbox
          checked={selectedRows.includes(record.id)}
          onChange={(e) => {
            if (e.target.checked) {
              setSelectedRows([...selectedRows, record.id])
            } else {
              setSelectedRows(selectedRows.filter(id => id !== record.id))
            }
          }}
        />
      )
    },
    {
      title: t('Status'),
      key: 'status',
      width: 100,
      render: (_, record) => (
        <Space>
          {record.pinned && <PushpinOutlined style={{ color: '#fa8c16' }} />}
          {record.archived && <InboxOutlined style={{ color: '#8c8c8c' }} />}
          <Badge 
            status={record.status === 'running' ? 'processing' : 
                   record.status === 'finished' ? 'success' : 
                   record.status === 'failed' ? 'error' : 'default'}
            text={record.status || 'unknown'}
          />
        </Space>
      )
    },
    {
      title: t('Project'),
      dataIndex: 'project',
      key: 'project',
      width: 150,
      render: (text) => (
        <Tag color="blue">
          <FolderOpenOutlined /> {text}
        </Tag>
      )
    },
    {
      title: t('Experiment'),
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space direction="vertical" size={0}>
          <a onClick={() => window.open(`/runs/${record.id}`, '_blank')}>
            <ExperimentOutlined /> {text}
          </a>
          <Typography.Text type="secondary" style={{ fontSize: 11 }}>{record.id}</Typography.Text>
        </Space>
      )
    },
    {
      title: t('Tags'),
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <Space wrap>
          {tags?.map((tag, i) => (
            <Tag key={i} color="cyan">{tag}</Tag>
          ))}
          <Button
            size="small"
            type="text"
            icon={<TagsOutlined />}
            onClick={() => {
              // Add tags functionality
            }}
          />
        </Space>
      )
    },
    {
      title: t('Created'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (ts) => new Date(ts * 1000).toLocaleString()
    },
    {
      title: t('Actions'),
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Dropdown
          menu={{
            items: [
              {
                key: 'view',
                icon: <EyeOutlined />,
                label: t('View Details'),
                onClick: () => {
                  setSelectedExp(record)
                  setDetailDrawerVisible(true)
                }
              },
              {
                key: 'env',
                icon: <InfoCircleOutlined />,
                label: t('View Environment'),
                onClick: () => handleViewEnvironment(record.id)
              },
              { type: 'divider' },
              {
                key: 'csv',
                icon: <ExportOutlined />,
                label: t('Export CSV'),
                onClick: () => handleExport(record.id, 'csv')
              },
              {
                key: 'report',
                icon: <DownloadOutlined />,
                label: t('Generate Report'),
                onClick: () => handleExport(record.id, 'markdown')
              },
              { type: 'divider' },
              {
                key: 'tag',
                icon: <TagsOutlined />,
                label: t('Manage Tags'),
                onClick: () => {
                  setSelectedExp(record)
                  setNewTags(record.tags || [])
                  setTagModalVisible(true)
                }
              },
              {
                key: 'pin',
                icon: <PushpinOutlined />,
                label: record.pinned ? t('Unpin') : t('Pin'),
                onClick: () => {
                  // Pin/unpin functionality
                }
              },
              { type: 'divider' },
              {
                key: 'delete',
                icon: <DeleteOutlined />,
                label: t('Delete'),
                danger: true,
                onClick: () => handleDelete([record.id])
              }
            ]
          }}
        >
          <Button type="text" icon={<MoreOutlined />} />
        </Dropdown>
      )
    }
  ]

  return (
    <div>
      {/* Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            placeholder={t('Select Project')}
            allowClear
            style={{ width: 150 }}
            value={filters.project}
            onChange={(value) => setFilters({ ...filters, project: value || '' })}
            options={allProjects.map(p => ({ label: p, value: p }))}
          />
          
          <Select
            mode="multiple"
            placeholder={t('Select Tags')}
            style={{ minWidth: 200 }}
            value={filters.tags}
            onChange={(value) => setFilters({ ...filters, tags: value })}
            options={allTags.map(t => ({ label: t, value: t }))}
          />
          
          <Input.Search
            placeholder={t('Search experiments...')}
            allowClear
            style={{ width: 250 }}
            value={filters.text}
            onChange={(e) => setFilters({ ...filters, text: e.target.value })}
          />
          
          <DatePicker.RangePicker
            onChange={(dates) => setFilters({ ...filters, dateRange: dates })}
          />
          
          <Checkbox
            checked={filters.archived}
            onChange={(e) => setFilters({ ...filters, archived: e.target.checked })}
          >
            {t('Show Archived')}
          </Checkbox>
          
          <Button 
            icon={<SyncOutlined />} 
            onClick={fetchExperiments}
          >
            {t('Refresh')}
          </Button>
        </Space>
      </Card>

      {/* Bulk Actions */}
      {selectedRows.length > 0 && (
        <Alert
          message={t(`${selectedRows.length} experiment(s) selected`)}
          type="info"
          showIcon
          action={
            <Space>
              <Button 
                danger
                size="small"
                onClick={() => handleDelete(selectedRows)}
              >
                {t('Delete Selected')}
              </Button>
              <Button 
                size="small"
                onClick={() => setSelectedRows([])}
              >
                {t('Clear Selection')}
              </Button>
            </Space>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Table */}
      <Table
        columns={columns}
        dataSource={experiments}
        rowKey="id"
        loading={loading}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          showTotal: (total) => t(`Total ${total} experiments`)
        }}
      />

      {/* Tag Modal */}
      <Modal
        title={t('Manage Tags')}
        open={tagModalVisible}
        onOk={handleAddTags}
        onCancel={() => setTagModalVisible(false)}
      >
        <Select
          mode="tags"
          style={{ width: '100%' }}
          placeholder={t('Add tags...')}
          value={newTags}
          onChange={setNewTags}
          options={allTags.map(t => ({ label: t, value: t }))}
        />
      </Modal>

      {/* Detail Drawer */}
      <Drawer
        title={t('Experiment Details')}
        placement="right"
        width={600}
        open={detailDrawerVisible}
        onClose={() => setDetailDrawerVisible(false)}
      >
        {selectedExp && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label={t('ID')}>{selectedExp.id}</Descriptions.Item>
            <Descriptions.Item label={t('Project')}>{selectedExp.project}</Descriptions.Item>
            <Descriptions.Item label={t('Name')}>{selectedExp.name}</Descriptions.Item>
            <Descriptions.Item label={t('Tags')}>
              <Space wrap>
                {selectedExp.tags?.map((tag, i) => (
                  <Tag key={i}>{tag}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label={t('Description')}>
              {selectedExp.description || t('No description')}
            </Descriptions.Item>
            <Descriptions.Item label={t('Created')}>
              {new Date(selectedExp.created_at * 1000).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label={t('Updated')}>
              {new Date(selectedExp.updated_at * 1000).toLocaleString()}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  )
}
