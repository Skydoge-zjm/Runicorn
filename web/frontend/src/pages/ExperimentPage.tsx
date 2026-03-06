import { useState, useCallback, useMemo, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Table, Button, Card, Space, Input, Tag, Tooltip, Empty, Badge, theme, App, Alert } from 'antd'
import { EyeOutlined, DeleteOutlined, CopyOutlined, PlusOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { softDeleteRuns, exportRunsZip, moveRuns } from '../api'
import { useExperimentData, type RunData } from '../hooks/useExperimentData'
import { useExperimentFilters } from '../hooks/useExperimentFilters'
import { useCompareMode } from '../hooks/useCompareMode'
import { useInlineEditing } from '../hooks/useInlineEditing'
import RecycleBin from '../components/RecycleBin'
import PathTreePanel from '../components/PathTreePanel'
import AddTagModal from '../components/AddTagModal'
import CompareRunsPanel from '../components/CompareRunsPanel'
import CompareChartsView from '../components/CompareChartsView'
import { ExperimentListSkeleton } from '../components/LoadingSkeleton'
import ResizableTitle from '../components/ResizableTitle'
import { useColumnWidths } from '../hooks/useColumnWidths'
import StatusTag from '../components/StatusTag'
import StatsBar from '../components/StatsBar'
import FilterToolbar from '../components/FilterToolbar'
import logger from '../utils/logger'
import { openExternal } from '../utils/tauri'
import type { ColumnsType } from 'antd/es/table'
import type { SorterResult } from 'antd/es/table/interface'
import '../styles/resizable-table.css'
import '../styles/enhanced-table.css'

// ECharts color palette (purple #b07cd0 lightened from default #9a60b4
// for Deuteranopia accessibility — original had near-identical luminance to blue)
const ECHARTS_COLORS = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
  '#3ba272', '#fc8452', '#b07cd0', '#ea7ccc'
]

interface ResizeCallbackData {
  size: { width: number }
}

const ExperimentPage: React.FC = () => {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { token } = theme.useToken()
  const { modal, message } = App.useApp()

  // Hooks
  const {
    runs, setRuns, loading, projects, stats,
    autoRefresh, setAutoRefresh,
    fetchRuns, handleBatchDeleteByPath, handleBatchExportByPath,
  } = useExperimentData(location.key)

  const {
    searchText, setSearchText,
    projectFilter, setProjectFilter,
    statusFilter, setStatusFilter,
    selectedTreePath, setSelectedTreePath,
    setSortedInfo,
    pageSize, setPageSize,
    treePanelCollapsed, setTreePanelCollapsed,
    treePanelWidth, isResizing, handleResizeStart,
    filteredRuns,
  } = useExperimentFilters(runs)

  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([])
  const [pathTreeRefresh, setPathTreeRefresh] = useState(0)
  const bumpPathTree = useCallback(() => setPathTreeRefresh(n => n + 1), [])

  const {
    compareMode, compareIdsFromUrl, needsMoreRuns,
    validRunIds, missingRunIds,
    compareRunInfos, compareMetrics, compareRunLabels,
    compareLoading, visibleRunIds,
    handleCompare, handleExitCompare,
    toggleRunVisibility, handleAddRuns,
  } = useCompareMode(runs, selectedRowKeys)

  // Sync selectedRowKeys when navigating with single compare ID (e.g. from "Compare with others" button)
  useEffect(() => {
    if (compareIdsFromUrl.length === 1) {
      setSelectedRowKeys([compareIdsFromUrl[0]])
    }
  }, [compareIdsFromUrl])

  const [hoveredRunId, setHoveredRunId] = useState<string | null>(null)

  const {
    editingRunId, editingAlias, setEditingAlias, aliasUpdateLoading,
    handleAliasEdit, handleAliasSave, handleAliasCancel,
    tagModalOpen, tagModalCurrentTags, allTagsFromRuns,
    handleRemoveTag, handleOpenTagModal,
    handleAddTagFromModal, handleCloseTagModal,
  } = useInlineEditing(runs, setRuns)

  // Column width management
  const defaultColumnWidths = {
    path: 180, alias: 120, tags: 180, run_id: 140,
    status: 100, created: 210, best_metric: 200, assets: 120, actions: 120,
  }
  const { columnWidths, setColumnWidth } = useColumnWidths('experiments', defaultColumnWidths)

  const handleResize = useCallback(
    (columnKey: string) =>
      (_: React.SyntheticEvent, { size }: ResizeCallbackData) => {
        setColumnWidth(columnKey, size.width)
      },
    [setColumnWidth]
  )

  // Local UI state
  const [recycleBinOpen, setRecycleBinOpen] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)

  // Delete handler
  const handleDelete = useCallback((explicitRunIds?: string[]) => {
    const idsToDelete = explicitRunIds || selectedRowKeys
    if (idsToDelete.length === 0) {
      message.warning(t('experiments.select_one_delete'))
      return
    }
    modal.confirm({
      title: t('experiments.move_to_bin_title'),
      content: (
        <div>
          <p>{t('experiments.soft_delete_confirm_content', { count: idsToDelete.length })}</p>
          <p style={{ color: token.colorPrimary, fontWeight: 500 }}>
            {t('experiments.soft_delete_note')}
          </p>
        </div>
      ),
      okText: t('experiments.move_to_bin'),
      okType: 'primary',
      cancelText: t('experiments.cancel'),
      okButtonProps: { loading: deleteLoading },
      onOk: async () => {
        setDeleteLoading(true)
        try {
          const result = await softDeleteRuns(idsToDelete)
          setSelectedRowKeys(prev => prev.filter(k => !idsToDelete.includes(k)))
          if (result.deleted_count > 0) {
            message.success(t('experiments.soft_delete_success', { count: result.deleted_count }))
            await fetchRuns(false)
            bumpPathTree()
          } else {
            message.warning(t('experiments.no_runs_moved'))
          }
        } catch (error) {
          logger.error('Delete failed:', error)
          message.error(t('experiments.delete_failed'))
        } finally {
          setDeleteLoading(false)
        }
      },
    })
  }, [selectedRowKeys, t, deleteLoading, fetchRuns, token, modal])

  // Export handler
  const handleExportZip = useCallback(async () => {
    if (selectedRowKeys.length === 0) return
    try {
      message.loading({ content: t('experiments.exporting'), key: 'export', duration: 0 })
      await exportRunsZip(selectedRowKeys)
      message.success({ content: t('experiments.export_success', { count: selectedRowKeys.length }), key: 'export' })
    } catch (error) {
      logger.error('Export failed:', error)
      message.error({ content: t('experiments.export_failed'), key: 'export' })
    }
  }, [selectedRowKeys, t])

  // Move handler (called from PathTreePanel drop)
  const handleMoveRuns = useCallback(async (runIds: string[], targetPath: string) => {
    try {
      const res = await moveRuns(runIds, targetPath)
      if (res.moved_count > 0) {
        message.success(t('experiments.move_success', { count: res.moved_count, path: targetPath }))
        setSelectedRowKeys(prev => prev.filter(k => !runIds.includes(k)))
        await fetchRuns(false)
        bumpPathTree()
      }
      if (res.failed_count > 0) {
        message.warning(t('experiments.move_partial_fail', { count: res.failed_count }))
      }
    } catch (error) {
      logger.error('Move failed:', error)
      message.error(t('experiments.move_failed'))
    }
  }, [t, fetchRuns])

  // Table columns
  const columns: ColumnsType<RunData> = useMemo(() => [
    {
      title: t('table.path'), dataIndex: 'path', key: 'path',
      sorter: (a, b) => a.path.localeCompare(b.path),
      render: (text) => (
        <Tooltip title={text}>
          <code style={{ fontSize: '12px', color: token.colorPrimary }}>{text}</code>
        </Tooltip>
      ),
      width: columnWidths.path,
      onHeaderCell: () => ({ width: columnWidths.path, onResize: handleResize('path') }),
    },
    {
      title: t('table.alias'), dataIndex: 'alias', key: 'alias',
      width: columnWidths.alias,
      sorter: (a, b) => (a.alias || '').localeCompare(b.alias || ''),
      render: (text, record) => {
        if (editingRunId === record.run_id) {
          return (
            <Input size="small" value={editingAlias}
              onChange={(e) => setEditingAlias(e.target.value)}
              onPressEnter={() => handleAliasSave(record.run_id)}
              onBlur={() => handleAliasSave(record.run_id)}
              onKeyDown={(e) => { if (e.key === 'Escape') handleAliasCancel() }}
              autoFocus style={{ width: '100%' }}
              placeholder={t('experiments.alias_placeholder')}
              disabled={aliasUpdateLoading}
            />
          )
        }
        return (
          <Tooltip title={t('experiments.double_click_edit')}>
            <div style={{ cursor: 'pointer', minHeight: 22, display: 'flex', alignItems: 'center' }}
              onDoubleClick={() => handleAliasEdit(record.run_id, text)}>
              {text ? <Tag color="purple">{text}</Tag> : <span style={{ color: token.colorTextDisabled }}>-</span>}
            </div>
          </Tooltip>
        )
      },
      onHeaderCell: () => ({ width: columnWidths.alias, onResize: handleResize('alias') }),
    },
    {
      title: t('table.tags'), dataIndex: 'tags', key: 'tags',
      width: columnWidths.tags,
      render: (tags: string[], record) => {
        const currentTags = tags || []
        return (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
            {currentTags.map(tag => (
              <Tag key={tag} closable onClose={(e) => { e.preventDefault(); e.stopPropagation(); handleRemoveTag(record.run_id, tag, currentTags) }} style={{ marginRight: 0 }}>{tag}</Tag>
            ))}
            <Tooltip title={t('experiments.add_tag')}>
              <Tag onClick={(e) => { e.stopPropagation(); handleOpenTagModal(record.run_id, currentTags) }}
                style={{ cursor: 'pointer', borderStyle: 'dashed', background: 'transparent' }}>
                <PlusOutlined />
              </Tag>
            </Tooltip>
          </div>
        )
      },
      onHeaderCell: () => ({ width: columnWidths.tags, onResize: handleResize('tags') }),
    },
    {
      title: t('table.run_id'), dataIndex: 'run_id', key: 'run_id',
      width: columnWidths.run_id,
      render: (text: string) => {
        const suffix = text.split('_').pop() || text.slice(-6)
        return (
          <Space size={4}>
            <Tooltip title={text}><code style={{ fontSize: '12px', cursor: 'pointer' }}>{suffix}</code></Tooltip>
            <Tooltip title={t('common.copy')}>
              <Button type="text" size="small" icon={<CopyOutlined style={{ fontSize: 12 }} />}
                style={{ padding: '0 4px', height: 20, minWidth: 20 }}
                onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(text); message.success(t('common.copied')) }}
              />
            </Tooltip>
          </Space>
        )
      },
      onHeaderCell: () => ({ width: columnWidths.run_id, onResize: handleResize('run_id') }),
    },
    {
      title: t('table.status'), dataIndex: 'status', key: 'status',
      width: columnWidths.status,
      sorter: (a, b) => a.status.localeCompare(b.status),
      onHeaderCell: () => ({ width: columnWidths.status, onResize: handleResize('status') }),
      render: (status) => <StatusTag status={status} />,
    },
    {
      title: t('table.created'), dataIndex: 'created', key: 'created',
      width: columnWidths.created,
      sorter: (a, b) => new Date(a.created).getTime() - new Date(b.created).getTime(),
      render: (text) => {
        const date = new Date(text)
        const locale = i18n.language === 'zh' ? 'zh-CN' : 'en-US'
        return (
          <span style={{ fontSize: '13px', whiteSpace: 'nowrap' }}>
            {date.toLocaleString(locale, { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
          </span>
        )
      },
      onHeaderCell: () => ({ width: columnWidths.created, onResize: handleResize('created') }),
    },
    {
      title: t('experiments.best_metric'), key: 'best_metric',
      width: columnWidths.best_metric,
      onHeaderCell: () => ({ width: columnWidths.best_metric, onResize: handleResize('best_metric') }),
      render: (_, record) => {
        const value = record.best_metric_value
        const name = record.best_metric_name
        if (value != null && name) {
          return (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '13px', color: token.colorTextSecondary, fontWeight: 500 }}>{name}</span>
              <span style={{ fontSize: '16px', fontWeight: 700, color: token.colorPrimary }}>{value.toFixed(4)}</span>
            </div>
          )
        }
        return '-'
      },
    },
    {
      title: t('experiments.assets'), key: 'assets',
      width: columnWidths.assets,
      onHeaderCell: () => ({ width: columnWidths.assets, onResize: handleResize('assets') }),
      render: (_, record) => {
        const count = record.assets_count || 0
        if (count === 0) return <span style={{ color: token.colorTextDisabled }}>-</span>
        return (
          <Tooltip title={t('experiments.assets_tip', { count })}>
            <Badge count={count} style={{ backgroundColor: token.colorSuccess }} />
          </Tooltip>
        )
      },
    },
    {
      title: t('table.actions'), key: 'actions',
      width: columnWidths.actions,
      onHeaderCell: () => ({ width: columnWidths.actions, onResize: handleResize('actions') }),
      render: (_, record) => (
        <Space size="small">
          <Tooltip title={t('table.view')}>
            <Button type="link" icon={<EyeOutlined />} onClick={() => navigate(`/runs/${record.run_id}`)} aria-label="View run details" />
          </Tooltip>
          <Tooltip title={t('experiments.delete')}>
            <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDelete([record.run_id])} aria-label="Delete run" />
          </Tooltip>
        </Space>
      ),
    },
  ], [t, navigate, columnWidths, handleResize, handleDelete, token, i18n.language,
    editingRunId, editingAlias, aliasUpdateLoading, handleAliasEdit, handleAliasSave,
    handleAliasCancel, handleRemoveTag, handleOpenTagModal])

  if (loading && runs.length === 0) return <ExperimentListSkeleton />

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', padding: 16 }}>
        <StatsBar stats={stats} />

        <div style={{ display: 'flex', gap: 16, flex: 1, minHeight: 0, overflow: 'hidden' }}>
          {/* Left panel: Compare or Path Tree */}
          {compareMode ? (
            <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
              style={{ width: 260, flexShrink: 0, borderRadius: 8, overflow: 'hidden', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', display: 'flex', flexDirection: 'column' }}>
              <CompareRunsPanel
                runs={compareRunInfos} colors={ECHARTS_COLORS}
                visibleRunIds={visibleRunIds} onToggleRunVisibility={toggleRunVisibility}
                onHoverRun={setHoveredRunId} hoveredRunId={hoveredRunId}
                onBack={handleExitCompare}
                style={{ height: '100%', minHeight: 0 }}
              />
            </motion.div>
          ) : (
            !treePanelCollapsed && (
              <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                style={{ width: treePanelWidth, flexShrink: 0, borderRadius: 8, overflow: 'hidden', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', display: 'flex', flexDirection: 'column', position: 'relative' }}>
                <PathTreePanel
                  selectedPath={selectedTreePath} onSelectPath={setSelectedTreePath}
                  onBatchDelete={async (path) => { await handleBatchDeleteByPath(path); bumpPathTree() }}
                  onBatchExport={handleBatchExportByPath}
                  onMoveRuns={handleMoveRuns}
                  refreshSignal={pathTreeRefresh}
                  style={{ height: '100%', minHeight: 0 }}
                />
                <div onMouseDown={handleResizeStart}
                  style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 4, cursor: 'col-resize', background: isResizing ? token.colorPrimary : 'transparent', transition: 'background 0.2s', zIndex: 10 }}
                  onMouseEnter={(e) => { if (!isResizing) (e.target as HTMLElement).style.background = token.colorPrimaryBg }}
                  onMouseLeave={(e) => { if (!isResizing) (e.target as HTMLElement).style.background = 'transparent' }}
                />
              </motion.div>
            )
          )}

          {/* Right: Filters + Table OR Compare Charts */}
          <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: 0 }}>
            {compareMode && !needsMoreRuns && validRunIds.length >= 2 ? (
              <>
                {missingRunIds.length > 0 && (
                  <Alert
                    type="warning"
                    message={t('experiments.compare_missing_runs', { ids: missingRunIds.join(', ') })}
                    style={{ marginBottom: 12 }}
                  />
                )}
                <CompareChartsView
                  runIds={compareRunInfos.map(r => r.runId)} visibleRunIds={visibleRunIds}
                  metricsMap={compareMetrics} runLabels={compareRunLabels}
                  colors={ECHARTS_COLORS} loading={compareLoading}
                  hoveredRunId={hoveredRunId} onHoverRun={setHoveredRunId}
                />
              </>
            ) : (
              <>
                {compareMode && missingRunIds.length > 0 && (
                  <Alert
                    type="warning"
                    message={t('experiments.compare_missing_runs', { ids: missingRunIds.join(', ') })}
                    style={{ marginBottom: 12 }}
                    action={
                      <Button size="small" onClick={handleExitCompare}>
                        {t('experiments.cancel')}
                      </Button>
                    }
                  />
                )}
                {needsMoreRuns && (
                  <Alert
                    type="info"
                    message={validRunIds.length === 0
                      ? t('experiments.compare_not_enough_runs')
                      : t('experiments.select_more_to_compare')}
                    style={{ marginBottom: 12 }}
                    action={
                      <Button size="small" onClick={handleExitCompare}>
                        {t('experiments.cancel')}
                      </Button>
                    }
                  />
                )}
                <FilterToolbar
                  searchText={searchText} onSearchChange={setSearchText}
                  projectFilter={projectFilter} onProjectFilterChange={setProjectFilter}
                  statusFilter={statusFilter} onStatusFilterChange={setStatusFilter}
                  projects={projects}
                  treePanelCollapsed={treePanelCollapsed} onToggleTreePanel={() => setTreePanelCollapsed(!treePanelCollapsed)}
                  loading={loading} autoRefresh={autoRefresh}
                  onRefresh={() => fetchRuns(true)} onAutoRefreshChange={setAutoRefresh}
                  selectedCount={selectedRowKeys.length}
                  onCompare={handleCompare} onDelete={() => handleDelete()}
                  onExportZip={handleExportZip}
                  onOpenRecycleBin={() => setRecycleBinOpen(true)}
                />

                <Card bordered={false}
                  style={{ borderRadius: 8, flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
                  styles={{ body: { padding: 0, flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' } }}>
                  <Table
                    className="enhanced-table"
                    components={{ header: { cell: ResizableTitle } }}
                    rowSelection={{
                      selectedRowKeys,
                      onChange: (keys) => setSelectedRowKeys(keys as string[]),
                      getCheckboxProps: () => ({ disabled: deleteLoading }),
                    }}
                    columns={columns} dataSource={filteredRuns} rowKey="run_id"
                    loading={loading}
                    pagination={{
                      pageSize, showSizeChanger: true, showQuickJumper: true,
                      pageSizeOptions: ['10', '20', '50', '100'],
                      onShowSizeChange: (_, size) => setPageSize(size),
                      showTotal: (total, range) => `${range[0]}-${range[1]} / ${total}`,
                    }}
                    scroll={{ x: 1200 }} size="middle"
                    onRow={(record) => ({
                      draggable: true,
                      onDragStart: (e: React.DragEvent) => {
                        const ids = selectedRowKeys.includes(record.run_id)
                          ? selectedRowKeys
                          : [record.run_id]
                        e.dataTransfer.setData('application/runicorn-run-ids', JSON.stringify(ids))
                        e.dataTransfer.effectAllowed = 'move'
                      },
                      onKeyDown: (e: React.KeyboardEvent) => { if (e.key === 'Enter') navigate(`/runs/${record.run_id}`) },
                      tabIndex: 0,
                    })}
                    onChange={(_, __, sorter) => setSortedInfo(sorter as SorterResult<RunData>)}
                    locale={{
                      emptyText: (
                        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE}
                          description={t('experiments.no_runs_desc')}>
                          <Button type="primary" onClick={() => openExternal('https://skydoge-zjm.github.io/Runicorn/getting-started/quickstart/')}>
                            {t('experiments.view_quickstart')}
                          </Button>
                        </Empty>
                      ),
                    }}
                  />
                </Card>
              </>
            )}
          </div>
        </div>
      </div>

      <RecycleBin open={recycleBinOpen} onClose={() => setRecycleBinOpen(false)} onRestore={() => { fetchRuns(false); bumpPathTree() }} />

      <AddTagModal open={tagModalOpen} existingTags={tagModalCurrentTags}
        allTags={allTagsFromRuns} onConfirm={handleAddTagFromModal} onClose={handleCloseTagModal} />
    </>
  )
}

export default ExperimentPage
