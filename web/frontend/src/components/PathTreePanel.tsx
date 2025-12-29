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
import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { Tree, Spin, Empty, Input, Tooltip, Dropdown, Modal } from 'antd'
import { FolderOutlined, FolderOpenOutlined, SearchOutlined, ReloadOutlined, DeleteOutlined, ExportOutlined, AppstoreOutlined, LoadingOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { motion, AnimatePresence } from 'framer-motion'
import type { DataNode, TreeProps } from 'antd/es/tree'
import type { MenuProps } from 'antd'
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
  style?: React.CSSProperties
}

// Custom styles for the tree
const treeStyles = `
  .path-tree-panel .ant-tree {
    background: transparent;
    font-size: 13px;
  }
  
  .path-tree-panel .ant-tree-treenode {
    padding: 0 4px;
    border-radius: 4px;
    transition: all 0.15s ease;
    align-items: center;
    min-height: 28px;
  }
  
  .path-tree-panel .ant-tree-treenode:hover {
    background: rgba(0, 0, 0, 0.04);
  }
  
  .path-tree-panel .ant-tree-treenode-selected {
    background: #e6f4ff !important;
  }
  
  .path-tree-panel .ant-tree-treenode-selected::before {
    content: '';
    position: absolute;
    left: 0;
    top: 2px;
    bottom: 2px;
    width: 3px;
    background: #1677ff;
    border-radius: 0 2px 2px 0;
  }
  
  .path-tree-panel .ant-tree-node-content-wrapper {
    padding: 2px 4px;
    border-radius: 4px;
    transition: all 0.15s ease;
  }
  
  .path-tree-panel .ant-tree-node-content-wrapper:hover {
    background: transparent;
  }
  
  .path-tree-panel .ant-tree-switcher {
    width: 20px;
    line-height: 28px;
    color: #faad14;
  }
  
  .path-tree-panel .ant-tree-indent-unit {
    width: 16px;
  }
  
  .path-tree-panel .ant-tree-list-holder-inner {
    padding: 4px 0;
  }
  
  /* Tree lines - more subtle */
  .path-tree-panel .ant-tree-indent-unit::before {
    border-color: #e8e8e8 !important;
  }
  
  .path-tree-panel .ant-tree-switcher-line-icon {
    color: #d9d9d9;
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
  stats?: Record<string, PathStats>
): DataNode[] => {
  const nodes: DataNode[] = []
  
  for (const [key, children] of Object.entries(tree)) {
    const currentPath = parentPath ? `${parentPath}/${key}` : key
    const hasChildren = Object.keys(children).length > 0
    const pathStats = stats?.[currentPath]
    
    nodes.push({
      key: currentPath,
      title: (
        <span style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: 6,
          width: '100%',
          paddingRight: 4,
        }}>
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
                color: '#999',
                padding: '1px 6px',
                background: '#f5f5f5',
                borderRadius: 10,
                fontWeight: 500,
              }}>
                {pathStats.total}
              </span>
            </span>
          )}
        </span>
      ),
      children: hasChildren ? buildTreeData(children, currentPath, stats) : undefined,
      isLeaf: !hasChildren,
    })
  }
  
  // Sort alphabetically
  return nodes.sort((a, b) => String(a.key).localeCompare(String(b.key)))
}

const PathTreePanel: React.FC<PathTreePanelProps> = ({
  selectedPath,
  onSelectPath,
  onBatchDelete,
  onBatchExport,
  style,
}) => {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [treeData, setTreeData] = useState<PathTreeData | null>(null)
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([])
  const [searchText, setSearchText] = useState('')
  const [contextMenuPath, setContextMenuPath] = useState<string | null>(null)
  const treeRef = useRef<HTMLDivElement>(null)

  // Inject custom styles
  useEffect(() => {
    const styleId = 'path-tree-panel-styles'
    if (!document.getElementById(styleId)) {
      const styleEl = document.createElement('style')
      styleEl.id = styleId
      styleEl.textContent = treeStyles
      document.head.appendChild(styleEl)
    }
  }, [])

  // Fetch path tree from API
  const fetchPathTree = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/paths?include_stats=true')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const data = await response.json()
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
  }, [])

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
    
    const nodes = buildTreeData(treeData.tree, '', treeData.stats)
    
    // Filter by search text
    if (searchText) {
      const filterTree = (nodes: DataNode[]): DataNode[] => {
        return nodes.filter(node => {
          const key = String(node.key).toLowerCase()
          const matches = key.includes(searchText.toLowerCase())
          
          if (node.children) {
            const filteredChildren = filterTree(node.children)
            if (filteredChildren.length > 0) {
              node.children = filteredChildren
              return true
            }
          }
          
          return matches
        })
      }
      return filterTree([...nodes])
    }
    
    return nodes
  }, [treeData, searchText])

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

  // Context menu items
  const contextMenuItems: MenuProps['items'] = [
    {
      key: 'delete',
      icon: <DeleteOutlined />,
      label: t('experiments.delete_path') || 'Delete all runs in this path',
      danger: true,
      onClick: () => {
        if (contextMenuPath && onBatchDelete) {
          Modal.confirm({
            title: t('experiments.delete_path_confirm_title') || 'Delete Path',
            content: t('experiments.delete_path_confirm', { path: contextMenuPath }) || 
              `Delete all runs under "${contextMenuPath}"?`,
            okText: t('experiments.delete') || 'Delete',
            okType: 'danger',
            onOk: () => onBatchDelete(contextMenuPath),
          })
        }
      },
    },
    {
      key: 'export',
      icon: <ExportOutlined />,
      label: t('experiments.export_path') || 'Export all runs in this path',
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

  if (loading && !treeData) {
    return (
      <div style={{ 
        ...style, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        padding: 24,
        background: '#fafafa',
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
        borderRight: '1px solid #f0f0f0',
        background: '#fafafa',
        outline: 'none',
      }}
    >
      {/* Header - fixed height */}
      <div style={{ 
        padding: '12px 12px 8px',
        borderBottom: '1px solid #f0f0f0',
        background: '#fff',
        flexShrink: 0,
      }}>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          marginBottom: 8,
        }}>
          <span style={{ fontWeight: 600, fontSize: 13, color: '#333' }}>
            <FolderOutlined style={{ marginRight: 6, color: '#faad14' }} />
            {t('experiments.path_tree') || 'Paths'}
          </span>
          <Tooltip title={t('runs.refresh') || 'Refresh'}>
            <ReloadOutlined 
              style={{ 
                cursor: 'pointer', 
                color: '#666',
                transition: 'color 0.2s',
              }}
              onClick={fetchPathTree}
              spin={loading}
            />
          </Tooltip>
        </div>
        <Input
          size="small"
          placeholder={t('experiments.search_path') || 'Search paths...'}
          prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
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
        <motion.div
          onClick={() => onSelectPath(null)}
          whileHover={{ backgroundColor: selectedPath === null ? '#e6f4ff' : 'rgba(0,0,0,0.04)' }}
          whileTap={{ scale: 0.98 }}
          style={{
            padding: '6px 12px',
            cursor: 'pointer',
            borderRadius: 4,
            margin: '0 4px 4px',
            background: selectedPath === null ? '#e6f4ff' : 'transparent',
            color: selectedPath === null ? '#1677ff' : '#333',
            fontWeight: selectedPath === null ? 600 : 400,
            fontSize: 13,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            position: 'relative',
            borderLeft: selectedPath === null ? '3px solid #1677ff' : '3px solid transparent',
            transition: 'all 0.15s ease',
          }}
        >
          <AppstoreOutlined style={{ color: selectedPath === null ? '#1677ff' : '#8c8c8c' }} />
          <span style={{ flex: 1 }}>{t('experiments.all_runs') || 'All Runs'}</span>
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
                color: '#999',
                padding: '1px 6px',
                background: selectedPath === null ? '#fff' : '#f5f5f5',
                borderRadius: 10,
                fontWeight: 500,
              }}>
                {totalStats.total}
              </span>
            </span>
          )}
        </motion.div>

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
                <div>
                  <Tree
                    showLine={{ showLeafIcon: false }}
                    switcherIcon={({ expanded }) => 
                      expanded 
                        ? <FolderOpenOutlined style={{ color: '#faad14' }} /> 
                        : <FolderOutlined style={{ color: '#faad14' }} />
                    }
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
                    ? (t('experiments.no_path_match') || 'No matching paths')
                    : (t('experiments.no_paths') || 'No paths yet')
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
              borderTop: '1px solid #f0f0f0',
              background: '#fff',
              fontSize: 12,
              color: '#666',
              overflow: 'hidden',
              flexShrink: 0,
            }}
          >
            <span style={{ color: '#999' }}>{t('experiments.filtering') || 'Filtering'}:</span>
            <code style={{ 
              marginLeft: 6, 
              color: '#1677ff',
              background: '#f0f5ff',
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
    </div>
  )
}

export default PathTreePanel
