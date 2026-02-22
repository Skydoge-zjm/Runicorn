import React from 'react'
import { Card, Space, Input, Select, Button, Checkbox, Dropdown, Tooltip } from 'antd'
import {
  SearchOutlined, ReloadOutlined, DeleteOutlined, ExportOutlined,
  LineChartOutlined, DownOutlined, FileExcelOutlined, FileTextOutlined,
  SyncOutlined, UndoOutlined, MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

interface FilterToolbarProps {
  // Filter state
  searchText: string
  onSearchChange: (value: string) => void
  projectFilter: string
  onProjectFilterChange: (value: string) => void
  statusFilter: string
  onStatusFilterChange: (value: string) => void
  projects: string[]
  // Tree panel
  treePanelCollapsed: boolean
  onToggleTreePanel: () => void
  // Refresh
  loading: boolean
  autoRefresh: boolean
  onRefresh: () => void
  onAutoRefreshChange: (checked: boolean) => void
  // Actions
  selectedCount: number
  onCompare: () => void
  onDelete: () => void
  onExportJSON: () => void
  onExportCSV: () => void
  onOpenRecycleBin: () => void
}

const FilterToolbar: React.FC<FilterToolbarProps> = ({
  searchText, onSearchChange,
  projectFilter, onProjectFilterChange,
  statusFilter, onStatusFilterChange,
  projects,
  treePanelCollapsed, onToggleTreePanel,
  loading, autoRefresh, onRefresh, onAutoRefreshChange,
  selectedCount, onCompare, onDelete, onExportJSON, onExportCSV,
  onOpenRecycleBin,
}) => {
  const { t } = useTranslation()

  const exportMenuItems = [
    {
      key: 'json',
      icon: <FileTextOutlined />,
      label: t('experiments.export_json') || 'Export as JSON',
      onClick: onExportJSON,
    },
    {
      key: 'csv',
      icon: <FileExcelOutlined />,
      label: t('experiments.export_csv') || 'Export as CSV',
      onClick: onExportCSV,
    },
  ]

  return (
    <Card
      bordered={false}
      size="small"
      style={{ borderRadius: 8, marginBottom: 12, flexShrink: 0 }}
      bodyStyle={{ padding: '12px 16px' }}
    >
      <Space style={{ width: '100%', justifyContent: 'space-between', flexWrap: 'wrap' }}>
        <Space wrap>
          <Tooltip title={treePanelCollapsed
            ? (t('experiments.show_tree') || 'Show path tree')
            : (t('experiments.hide_tree') || 'Hide path tree')
          }>
            <Button
              icon={treePanelCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={onToggleTreePanel}
            />
          </Tooltip>
          <Input
            placeholder={t('experiments.search_placeholder') || 'Search runs...'}
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => onSearchChange(e.target.value)}
            style={{ width: 180 }}
            allowClear
          />
          <Select
            value={projectFilter}
            onChange={onProjectFilterChange}
            style={{ width: 140 }}
            options={[
              { value: 'all', label: t('experiments.all_projects') || 'All Projects' },
              ...projects.map(p => ({ value: p, label: p }))
            ]}
          />
          <Select
            value={statusFilter}
            onChange={onStatusFilterChange}
            style={{ width: 120 }}
            options={[
              { value: 'all', label: t('experiments.all_status') || 'All Status' },
              { value: 'running', label: t('experiments.running') || 'Running' },
              { value: 'finished', label: t('experiments.finished') || 'Finished' },
              { value: 'failed', label: t('experiments.failed') || 'Failed' },
            ]}
          />
          <Button
            icon={autoRefresh ? <SyncOutlined spin /> : <ReloadOutlined />}
            onClick={onRefresh}
            loading={loading}
          >
            {t('runs.refresh') || 'Refresh'}
          </Button>
          <Checkbox
            checked={autoRefresh}
            onChange={(e) => onAutoRefreshChange(e.target.checked)}
          >
            {t('experiments.auto_refresh') || 'Auto'}
          </Checkbox>
          <Button icon={<UndoOutlined />} onClick={onOpenRecycleBin}>
            {t('experiments.recycle_bin') || 'Bin'}
          </Button>
        </Space>

        <Space>
          {selectedCount > 0 && (
            <>
              <Button icon={<LineChartOutlined />} onClick={onCompare} disabled={selectedCount < 2}>
                {t('experiments.compare') || 'Compare'} ({selectedCount})
              </Button>
              <Dropdown menu={{ items: exportMenuItems }} trigger={['click']}>
                <Button icon={<ExportOutlined />}>
                  {t('experiments.export') || 'Export'} ({selectedCount}) <DownOutlined />
                </Button>
              </Dropdown>
              <Button danger icon={<DeleteOutlined />} onClick={onDelete}>
                {t('experiments.delete') || 'Delete'} ({selectedCount})
              </Button>
            </>
          )}
        </Space>
      </Space>
    </Card>
  )
}

export default FilterToolbar
