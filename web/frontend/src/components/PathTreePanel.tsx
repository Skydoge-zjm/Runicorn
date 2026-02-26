/**
 * PathTreePanel - VSCode-style path tree navigation for experiments
 * 
 * Displays a hierarchical tree of experiment paths, allowing users to
 * filter runs by selecting a path node.
 * 
 * Features:
 * - Hierarchical path display with folder icons
 * - Run count badges per path
 * - Search/filter functionality
 * - Right-click context menu for batch operations
 * - Keyboard navigation support
 * - Smooth animations
 */
import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { Tree, Spin, Empty, Input, Tooltip, Dropdown, App, Modal, message, theme } from 'antd'
import { FolderOutlined, FolderFilled, FolderOpenFilled, FolderAddOutlined, SearchOutlined, ReloadOutlined, DeleteOutlined, ExportOutlined, AppstoreOutlined, LoadingOutlined, PlusOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { motion, AnimatePresence } from 'framer-motion'
import type { DataNode, TreeProps } from 'antd/es/tree'
import type { MenuProps } from 'antd'
import { listPaths, createPath } from '../api'
import logger from '../utils/logger'

interface PathStats {
  total: number
  running: number
  finished: number
  failed: number
}

interface PathTreeData {
  paths: string[]
  tree: Record<string, any>
  stats?: Record<string, PathStats>
}

interface PathTreePanelProps {
  selectedPath: string | null
  onSelectPath: (path: string | null) => void
  onBatchDelete?: (path: string) => void
  onBatchExport?: (path: string) => void
  onMoveRuns?: (runIds: string[], targetPath: string) => void
  /** Increment to trigger a tree refresh from the parent */
  refreshSignal?: number
  style?: React.CSSProperties
}

// Build theme-aware custom styles for the tree
const buildTreeStyles = (token: any) => `
  .path-tree-panel .ant-tree {
    background: transparent;
    font-size: 13px;
  }
  
  .path-tree-panel .ant-tree-treenode {
    padding: 0 4px !important;
    border-radius: 4px;
    transition: all 0.15s ease;
    align-items: center;
    min-height: 20px;
  }
  
  .path-tree-panel .ant-tree-treenode:hover {
    background: ${token?.colorFillTertiary || 'rgba(255,255,255,0.08)'};
  }
  
  .path-tree-panel .ant-tree-treenode-selected {
    background: ${token?.colorPrimaryBg || 'rgba(22,119,255,0.16)'} !important;
  }

  .path-tree-panel .ant-tree-treenode-selected:hover {
    background: ${token?.colorPrimaryBg || 'rgba(22,119,255,0.16)'} !important;
  }
  
  .path-tree-panel .ant-tree-treenode-selected::before {
    content: '';
    position: absolute;
    left: 0;
    top: 2px;
    bottom: 2px;
    width: 3px;
    background: ${token?.colorPrimary || '#1677ff'};
    border-radius: 0 2px 2px 0;
  }

  .path-tree-panel .ant-tree-node-content-wrapper.ant-tree-node-selected {
    background: transparent !important;
  }
  
  .path-tree-panel .ant-tree-node-content-wrapper {
    padding: 0 4px;
    border-radius: 4px;
    transition: all 0.15s ease;
    line-height: 22px;
  }
  
  .path-tree-panel .ant-tree-node-content-wrapper:hover {
    background: transparent;
  }
  
  .path-tree-panel .ant-tree-switcher {
    width: 18px;
    line-height: 22px;
    display: inline-flex !important;
    align-items: center;
    justify-content: center;
  }
  
  .path-tree-panel .ant-tree-switcher .ant-tree-switcher-icon {
    font-size: 9px !important;
    color: ${token?.colorTextTertiary || '#8c8c8c'};
    transition: transform 0.15s ease;
  }
  
  .path-tree-panel .ant-tree-indent {
    align-self: stretch;
    display: inline-flex !important;
  }
  
  .path-tree-panel .ant-tree-indent-unit {
    width: 14px;
    position: relative;
    align-self: stretch;
  }
  
  .path-tree-panel .ant-tree-indent-unit::before {
    content: '';
    position: absolute;
    top: -2px;
    bottom: -2px;
    left: 6px;
    width: 1px;
    background: ${token?.colorTextQuaternary || '#8c8c8c'};
    pointer-events: none;
  }
  
  .path-tree-panel .ant-tree-treenode {
    overflow: visible;
  }
  
  .path-tree-panel .ant-tree-list-holder-inner {
    padding: 2px 0;
  }
  
  .path-tree-panel .all-runs-item:hover {
    background: ${token?.colorFillTertiary || 'rgba(255,255,255,0.08)'} !important;
  }
  
  .path-tree-panel .all-runs-item.all-runs-selected:hover {
    background: ${token?.colorPrimaryBg || 'rgba(22,119,255,0.16)'} !important;
  }
  
  /* Running indicator pulse animation */
  @keyframes pulse-ring {
    0% { transform: scale(0.8); opacity: 1; }
    100% { transform: scale(1.4); opacity: 0; }
  }
  
  .running-indicator {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 12px;
    height: 12px;
  }
  
  .running-indicator::before {
    content: '';
    position: absolute;
    width: 8px;
    height: 8px;
    background: #52c41a;
    border-radius: 50%;
    animation: pulse-ring 1.5s ease-out infinite;
  }
  
  .running-indicator::after {
    content: '';
    width: 6px;
    height: 6px;
    background: #52c41a;
    border-radius: 50%;
  }
`

// Convert nested tree object to Ant Design Tree DataNode format
const buildTreeData = (
  tree: Record<string, any>,
  parentPath: string = '',
  stats?: Record<string, PathStats>,
  token?: any,
  dropTargetPath?: string | null,
  expandedKeys?: React.Key[],
): DataNode[] => {
  const nodes: DataNode[] = []
  
  for (const [key, children] of Object.entries(tree)) {
    const currentPath = parentPath ? `${parentPath}/${key}` : key
    const hasChildren = Object.keys(children).length > 0
    const pathStats = stats?.[currentPath]
    const isDropTarget = dropTargetPath === currentPath
    const isExpanded = expandedKeys?.includes(currentPath)
    
    nodes.push({
      key: currentPath,
      title: (
        <span style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: 6,
          width: '100%',
          paddingRight: 4,
          borderRadius: 4,
          outline: isDropTarget ? `2px dashed ${token?.colorPrimary || '#1677ff'}` : 'none',
          background: isDropTarget ? (token?.colorPrimaryBgHover || 'rgba(22,119,255,0.12)') : 'transparent',
          transition: 'outline 0.1s, background 0.1s',
        }}>
          {isExpanded
            ? <FolderOpenFilled style={{ color: token?.colorWarning || '#faad14', fontSize: 14, flexShrink: 0 }} />
            : <FolderFilled style={{ color: token?.colorWarning || '#faad14', fontSize: 14, flexShrink: 0 }} />
          }
          <span style={{ 
            flex: 1, 
            overflow: 'hidden', 
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            {key}
          </span>
          {pathStats && (
            <span style={{ 
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              marginLeft: 'auto',
              flexShrink: 0,
            }}>
              {pathStats.running > 0 && (
                <Tooltip title={`${pathStats.running} running`}>
                  <span className="running-indicator" />
                </Tooltip>
              )}
              <span style={{ 
                fontSize: 10, 
                color: token?.colorTextSecondary || '#999',
                padding: '1px 6px',
                background: token?.colorFillTertiary || '#f5f5f5',
                borderRadius: 10,
                fontWeight: 500,
              }}>
                {pathStats.total}
              </span>
            </span>
          )}
        </span>
      ),
      children: hasChildren ? buildTreeData(children, currentPath, stats, token, dropTargetPath, expandedKeys) : undefined,
      isLeaf: !hasChildren,
    })
  }
  
  // Sort alphabetically
  return nodes.sort((a, b) => String(a.key).localeCompare(String(b.key)))
}

const DRAG_MIME = 'application/runicorn-run-ids'

const PathTreePanel: React.FC<PathTreePanelProps> = ({
  selectedPath,
  onSelectPath,
  onBatchDelete,
  onBatchExport,
  onMoveRuns,
  refreshSignal,
  style,
}) => {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const { modal } = App.useApp()
  const [loading, setLoading] = useState(false)
  const [treeData, setTreeData] = useState<PathTreeData | null>(null)
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([])
  const [searchText, setSearchText] = useState('')
  const [contextMenuPath, setContextMenuPath] = useState<string | null>(null)
  const [dropTargetPath, setDropTargetPath] = useState<string | null>(null)
  const [newFolderParent, setNewFolderParent] = useState<string | null>(null)
  const [newFolderName, setNewFolderName] = useState('')
  const treeRef = useRef<HTMLDivElement>(null)

  const treeStyles = useMemo(
    () => buildTreeStyles(token),
    [token.colorFillTertiary, token.colorPrimaryBg, token.colorPrimary, token.colorWarning, token.colorBorderSecondary, token.colorTextQuaternary]
  )

  // Inject/update theme-aware custom styles
  useEffect(() => {
    const styleId = 'path-tree-panel-styles'
    const existing = document.getElementById(styleId) as HTMLStyleElement | null
    if (existing) {
      existing.textContent = treeStyles
    } else {
      const styleEl = document.createElement('style')
      styleEl.id = styleId
      styleEl.textContent = treeStyles
      document.head.appendChild(styleEl)
    }
  }, [treeStyles])

  // Fetch path tree from API
  const fetchPathTree = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listPaths(true)
      setTreeData(data)
      
      // Auto-expand first level on initial load
      if (data.tree && expandedKeys.length === 0) {
        const firstLevelKeys = Object.keys(data.tree)
        setExpandedKeys(firstLevelKeys)
      }
    } catch (error) {
      logger.error('Failed to fetch path tree:', error)
    } finally {
      setLoading(false)
    }
  }, [expandedKeys.length])

  useEffect(() => {
    fetchPathTree()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Re-fetch when parent signals a data change
  useEffect(() => {
    if (refreshSignal && refreshSignal > 0) {
      fetchPathTree()
    }
  }, [refreshSignal]) // eslint-disable-line react-hooks/exhaustive-deps

  // Persist expanded keys to localStorage
  useEffect(() => {
    if (expandedKeys.length > 0) {
      localStorage.setItem('path_tree_expanded', JSON.stringify(expandedKeys))
    }
  }, [expandedKeys])

  // Restore expanded keys from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('path_tree_expanded')
    if (saved) {
      try {
        const keys = JSON.parse(saved)
        if (Array.isArray(keys)) {
          setExpandedKeys(keys)
        }
      } catch {}
    }
  }, [])

  // Calculate total stats
  const totalStats = useMemo(() => {
    if (!treeData?.stats) return null
    
    let total = 0, running = 0, finished = 0, failed = 0
    
    // Only count root-level paths to avoid double counting
    for (const path of Object.keys(treeData.stats)) {
      if (!path.includes('/')) {
        const s = treeData.stats[path]
        total += s.total
        running += s.running
        finished += s.finished
        failed += s.failed
      }
    }
    
    return { total, running, finished, failed }
  }, [treeData?.stats])

  // Build tree nodes with search filtering
  const treeNodes = useMemo(() => {
    if (!treeData?.tree) return []
    
    const nodes = buildTreeData(treeData.tree, '', treeData.stats, token, dropTargetPath, expandedKeys)
    
    // Filter by search text
    if (searchText) {
      const filterTree = (nodes: DataNode[]): DataNode[] => {
        return nodes.flatMap(node => {
          const key = String(node.key).toLowerCase()
          const matches = key.includes(searchText.toLowerCase())
          
          if (node.children) {
            const filteredChildren = filterTree(node.children)
            if (filteredChildren.length > 0) {
              return [{ ...node, children: filteredChildren }]
            }
          }
          
          return matches ? [node] : []
        })
      }
      return filterTree(nodes)
    }
    
    return nodes
  }, [treeData, searchText, token, dropTargetPath, expandedKeys])

  // Handle tree node selection
  const handleSelect: TreeProps['onSelect'] = (selectedKeys) => {
    if (selectedKeys.length === 0) {
      onSelectPath(null)
    } else {
      const path = String(selectedKeys[0])
      // Toggle selection: click again to deselect
      if (path === selectedPath) {
        onSelectPath(null)
      } else {
        onSelectPath(path)
      }
    }
  }

  // Handle expand/collapse
  const handleExpand: TreeProps['onExpand'] = (keys) => {
    setExpandedKeys(keys)
  }

  // Create folder handler
  const handleCreateFolder = useCallback(async () => {
    const name = newFolderName.trim()
    if (!name) return
    const fullPath = newFolderParent ? `${newFolderParent}/${name}` : name
    try {
      await createPath(fullPath)
      message.success(t('experiments.folder_created', { path: fullPath }))
      setNewFolderParent(null)
      setNewFolderName('')
      fetchPathTree()
    } catch (e: any) {
      message.error(typeof e?.message === 'string' ? e.message : t('experiments.folder_create_failed'))
    }
  }, [newFolderName, newFolderParent, t, fetchPathTree])

  // Context menu items
  const contextMenuItems: MenuProps['items'] = [
    {
      key: 'new_folder',
      icon: <FolderAddOutlined />,
      label: t('experiments.new_subfolder'),
      onClick: () => {
        if (contextMenuPath) {
          setNewFolderParent(contextMenuPath)
          setNewFolderName('')
        }
      },
    },
    { type: 'divider' },
    {
      key: 'delete',
      icon: <DeleteOutlined />,
      label: t('experiments.delete_path'),
      danger: true,
      onClick: () => {
        if (contextMenuPath && onBatchDelete) {
          modal.confirm({
            title: t('experiments.delete_path_confirm_title'),
            content: t('experiments.delete_path_confirm', { path: contextMenuPath }),
            okText: t('experiments.delete'),
            okType: 'danger',
            onOk: () => onBatchDelete(contextMenuPath),
          })
        }
      },
    },
    {
      key: 'export',
      icon: <ExportOutlined />,
      label: t('experiments.export_path'),
      onClick: () => {
        if (contextMenuPath && onBatchExport) {
          onBatchExport(contextMenuPath)
        }
      },
    },
  ]

  // Handle right-click on tree node
  const handleRightClick: TreeProps['onRightClick'] = ({ node }) => {
    setContextMenuPath(String(node.key))
  }

  // --- Drag-and-drop handlers ---
  const handleDragOver = useCallback((path: string) => (e: React.DragEvent) => {
    if (!e.dataTransfer.types.includes(DRAG_MIME)) return
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDropTargetPath(path)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    // Only clear if leaving the node (not entering a child)
    const related = e.relatedTarget as HTMLElement | null
    if (related && (e.currentTarget as HTMLElement).contains(related)) return
    setDropTargetPath(null)
  }, [])

  const handleDrop = useCallback((path: string) => (e: React.DragEvent) => {
    e.preventDefault()
    setDropTargetPath(null)
    const raw = e.dataTransfer.getData(DRAG_MIME)
    if (!raw || !onMoveRuns) return
    try {
      const ids: string[] = JSON.parse(raw)
      if (ids.length > 0) {
        onMoveRuns(ids, path)
      }
    } catch {
      // ignore
    }
  }, [onMoveRuns])

  if (loading && !treeData) {
    return (
      <div style={{ 
        ...style, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        padding: 24,
        background: token.colorBgContainer,
      }}>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
      </div>
    )
  }

  return (
    <div 
      ref={treeRef}
      className="path-tree-panel"
      tabIndex={0}
      style={{ 
        ...style,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: 0,  // Important for flex child to allow shrinking
        borderRight: `1px solid ${token.colorBorderSecondary}`,
        background: token.colorBgContainer,
        outline: 'none',
      }}
    >
      {/* Header - fixed height */}
      <div style={{ 
        padding: '12px 12px 8px',
        borderBottom: `1px solid ${token.colorBorderSecondary}`,
        background: token.colorBgContainer,
        flexShrink: 0,
      }}>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          marginBottom: 8,
        }}>
          <span style={{ fontWeight: 600, fontSize: 13, color: token.colorText }}>
            <FolderOutlined style={{ marginRight: 6, color: token.colorWarning }} />
            {t('experiments.path_tree')}
          </span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Tooltip title={t('experiments.new_folder')}>
              <PlusOutlined
                style={{ cursor: 'pointer', color: token.colorTextSecondary, fontSize: 12 }}
                onClick={() => { setNewFolderParent(''); setNewFolderName('') }}
              />
            </Tooltip>
            <Tooltip title={t('runs.refresh')}>
              <ReloadOutlined 
                style={{ 
                  cursor: 'pointer', 
                  color: token.colorTextSecondary,
                  transition: 'color 0.2s',
                }}
                onClick={fetchPathTree}
                spin={loading}
              />
            </Tooltip>
          </div>
        </div>
        <Input
          size="small"
          placeholder={t('experiments.search_path')}
          prefix={<SearchOutlined style={{ color: token.colorTextQuaternary }} />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
          style={{ borderRadius: 6 }}
        />
      </div>

      {/* Tree content - scrollable */}
      <div style={{ 
        flex: 1, 
        overflow: 'auto',
        padding: '4px 0',
        minHeight: 0,  // Important for flex child scrolling
      }}>
        {/* "All Runs" option */}
        <Dropdown
          menu={{ items: [{
            key: 'new_folder',
            icon: <FolderAddOutlined />,
            label: t('experiments.new_folder'),
            onClick: () => { setNewFolderParent(''); setNewFolderName('') },
          }] }}
          trigger={['contextMenu']}
        >
        <div
          className={`all-runs-item${selectedPath === null ? ' all-runs-selected' : ''}`}
          onClick={() => onSelectPath(null)}
          onDragOver={handleDragOver('default')}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop('default')}
          style={{
            padding: '6px 12px',
            cursor: 'pointer',
            borderRadius: 4,
            margin: '0 4px 4px',
            background: dropTargetPath === 'default'
              ? token.colorPrimaryBgHover
              : selectedPath === null ? token.colorPrimaryBg : 'transparent',
            color: selectedPath === null ? token.colorPrimary : token.colorText,
            fontWeight: selectedPath === null ? 600 : 400,
            fontSize: 13,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            position: 'relative',
            borderLeft: selectedPath === null ? `3px solid ${token.colorPrimary}` : '3px solid transparent',
            outline: dropTargetPath === 'default' ? `2px dashed ${token.colorPrimary}` : 'none',
            transition: 'all 0.15s ease',
          }}
        >
          <AppstoreOutlined style={{ color: selectedPath === null ? token.colorPrimary : token.colorTextTertiary }} />
          <span style={{ flex: 1 }}>{t('experiments.all_runs')}</span>
          {totalStats && (
            <span style={{ 
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}>
              {totalStats.running > 0 && (
                <span className="running-indicator" />
              )}
              <span style={{ 
                fontSize: 10, 
                color: token.colorTextSecondary,
                padding: '1px 6px',
                background: selectedPath === null ? token.colorBgContainer : token.colorFillTertiary,
                borderRadius: 10,
                fontWeight: 500,
              }}>
                {totalStats.total}
              </span>
            </span>
          )}
        </div>
        </Dropdown>

        {/* Path tree */}
        <AnimatePresence mode="wait">
          {treeNodes.length > 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <Dropdown
                menu={{ items: contextMenuItems }}
                trigger={['contextMenu']}
              >
                <div
                  onDragOver={(e) => {
                    // Find closest tree node to highlight
                    if (!e.dataTransfer.types.includes(DRAG_MIME)) return
                    e.preventDefault()
                    e.dataTransfer.dropEffect = 'move'
                    const target = (e.target as HTMLElement).closest('.ant-tree-treenode') as HTMLElement | null
                    if (target) {
                      const key = target.getAttribute('data-key') || target.querySelector('.ant-tree-node-content-wrapper')?.closest('[data-key]')?.getAttribute('data-key')
                      // Try to find key from the tree node's title
                      const titleEl = target.querySelector('.ant-tree-node-content-wrapper')
                      if (titleEl) {
                        // Walk treeNodes to find matching key by DOM position
                        const allNodes = treeRef.current?.querySelectorAll('.ant-tree-treenode')
                        if (allNodes) {
                          const idx = Array.from(allNodes).indexOf(target)
                          // Flatten tree to get key by index
                          const flatKeys: string[] = []
                          const flatten = (nodes: DataNode[]) => {
                            for (const n of nodes) {
                              flatKeys.push(String(n.key))
                              if (n.children && expandedKeys.includes(n.key)) flatten(n.children)
                            }
                          }
                          flatten(treeNodes)
                          if (idx >= 0 && idx < flatKeys.length) {
                            setDropTargetPath(flatKeys[idx])
                            return
                          }
                        }
                      }
                      if (key) setDropTargetPath(key)
                    }
                  }}
                  onDragLeave={(e) => {
                    const related = e.relatedTarget as HTMLElement | null
                    if (related && (e.currentTarget as HTMLElement).contains(related)) return
                    setDropTargetPath(null)
                  }}
                  onDrop={(e) => {
                    e.preventDefault()
                    if (dropTargetPath && dropTargetPath !== 'default') {
                      const raw = e.dataTransfer.getData(DRAG_MIME)
                      if (raw && onMoveRuns) {
                        try {
                          const ids: string[] = JSON.parse(raw)
                          if (ids.length > 0) onMoveRuns(ids, dropTargetPath)
                        } catch {}
                      }
                    }
                    setDropTargetPath(null)
                  }}
                >
                  <Tree
                    blockNode
                    treeData={treeNodes}
                    selectedKeys={selectedPath ? [selectedPath] : []}
                    expandedKeys={expandedKeys}
                    onSelect={handleSelect}
                    onExpand={handleExpand}
                    onRightClick={handleRightClick}
                  />
                </div>
              </Dropdown>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <Empty 
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  searchText 
                    ? (t('experiments.no_path_match'))
                    : (t('experiments.no_paths'))
                }
                style={{ marginTop: 32 }}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Selected path indicator - fixed at bottom */}
      <AnimatePresence>
        {selectedPath && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{
              padding: '8px 12px',
              borderTop: `1px solid ${token.colorBorderSecondary}`,
              background: token.colorBgContainer,
              fontSize: 12,
              color: token.colorTextSecondary,
              overflow: 'hidden',
              flexShrink: 0,
            }}
          >
            <span style={{ color: token.colorTextTertiary }}>{t('experiments.filtering')}:</span>
            <code style={{ 
              marginLeft: 6, 
              color: token.colorPrimary,
              background: token.colorPrimaryBg,
              padding: '2px 8px',
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 500,
            }}>
              {selectedPath}
            </code>
          </motion.div>
        )}
      </AnimatePresence>

      {/* New Folder Modal */}
      <Modal
        title={t('experiments.new_folder')}
        open={newFolderParent !== null}
        onCancel={() => setNewFolderParent(null)}
        onOk={handleCreateFolder}
        okText={t('experiments.create')}
        cancelText={t('experiments.cancel')}
        width={380}
        destroyOnClose
      >
        {newFolderParent !== null && (
          <div>
            {newFolderParent && (
              <div style={{ marginBottom: 8, fontSize: 12, color: token.colorTextSecondary }}>
                {t('experiments.parent_path')}: <code style={{ color: token.colorPrimary }}>{newFolderParent}</code>
              </div>
            )}
            <Input
              placeholder={t('experiments.folder_name_placeholder')}
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              onPressEnter={handleCreateFolder}
              autoFocus
            />
          </div>
        )}
      </Modal>
    </div>
  )
}

export default PathTreePanel
