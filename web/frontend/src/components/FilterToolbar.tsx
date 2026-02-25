import { Card, Space, Input, Select, Button, Checkbox, Tooltip } from 'antd'
import {
  SearchOutlined, ReloadOutlined, DeleteOutlined, ExportOutlined,
  LineChartOutlined,
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
  onExportZip: () => void
  onOpenRecycleBin: () => void
}

const FilterToolbar: React.FC<FilterToolbarProps> = ({
  searchText, onSearchChange,
  projectFilter, onProjectFilterChange,
  statusFilter, onStatusFilterChange,
  projects,
  treePanelCollapsed, onToggleTreePanel,
  loading, autoRefresh, onRefresh, onAutoRefreshChange,
  selectedCount, onCompare, onDelete, onExportZip,
  onOpenRecycleBin,
}) => {
  const { t } = useTranslation()


  return (
    <Card
      bordered={false}
      size="small"
      style={{ borderRadius: 8, marginBottom: 12, flexShrink: 0 }}
      styles={{ body: { padding: '12px 16px' } }}
    >
      <Space style={{ width: '100%', justifyContent: 'space-between', flexWrap: 'wrap' }}>
        <Space wrap>
          <Tooltip title={treePanelCollapsed
            ? (t('experiments.show_tree'))
            : (t('experiments.hide_tree'))
          }>
            <Button
              icon={treePanelCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={onToggleTreePanel}
            />
          </Tooltip>
          <Input
            placeholder={t('experiments.search_placeholder')}
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
              { value: 'all', label: t('experiments.all_projects') },
              ...projects.map(p => ({ value: p, label: p }))
            ]}
          />
          <Select
            value={statusFilter}
            onChange={onStatusFilterChange}
            style={{ width: 120 }}
            options={[
              { value: 'all', label: t('experiments.all_status') },
              { value: 'running', label: t('experiments.running') },
              { value: 'finished', label: t('experiments.finished') },
              { value: 'failed', label: t('experiments.failed') },
            ]}
          />
          <Button
            icon={autoRefresh ? <SyncOutlined spin /> : <ReloadOutlined />}
            onClick={onRefresh}
            loading={loading}
          >
            {t('runs.refresh')}
          </Button>
          <Checkbox
            checked={autoRefresh}
            onChange={(e) => onAutoRefreshChange(e.target.checked)}
          >
            {t('experiments.auto_refresh')}
          </Checkbox>
          <Button icon={<UndoOutlined />} onClick={onOpenRecycleBin}>
            {t('experiments.recycle_bin')}
          </Button>
        </Space>

        <Space>
          {selectedCount > 0 && (
            <>
              <Button icon={<LineChartOutlined />} onClick={onCompare} disabled={selectedCount < 2}>
                {t('experiments.compare')} ({selectedCount})
              </Button>
              <Button icon={<ExportOutlined />} onClick={onExportZip}>
                {t('experiments.export')} ({selectedCount})
              </Button>
              <Button danger icon={<DeleteOutlined />} onClick={onDelete}>
                {t('experiments.delete')} ({selectedCount})
              </Button>
            </>
          )}
        </Space>
      </Space>
    </Card>
  )
}

export default FilterToolbar
