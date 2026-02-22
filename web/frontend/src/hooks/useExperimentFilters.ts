import { useState, useMemo, useCallback, useEffect } from 'react'
import type { SorterResult } from 'antd/es/table/interface'
import type { RunData } from './useExperimentData'

export function useExperimentFilters(runs: RunData[]) {
  const [searchText, setSearchText] = useState('')
  const [projectFilter, setProjectFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedTreePath, setSelectedTreePath] = useState<string | null>(null)
  const [sortedInfo, setSortedInfo] = useState<SorterResult<RunData>>({})
  const [pageSize, setPageSize] = useState(10)

  // Persist / restore pageSize
  useEffect(() => {
    const saved = localStorage.getItem('experiment_preferences')
    if (saved) {
      try {
        const prefs = JSON.parse(saved)
        if (prefs.pageSize) setPageSize(prefs.pageSize)
      } catch {}
    }
  }, [])

  useEffect(() => {
    localStorage.setItem('experiment_preferences', JSON.stringify({ pageSize }))
  }, [pageSize])

  // Tree panel state
  const [treePanelCollapsed, setTreePanelCollapsed] = useState(() => {
    return localStorage.getItem('tree_panel_collapsed') === 'true'
  })
  const [treePanelWidth, setTreePanelWidth] = useState(() => {
    const saved = localStorage.getItem('tree_panel_width')
    return saved ? parseInt(saved, 10) : 240
  })
  const [isResizing, setIsResizing] = useState(false)

  useEffect(() => {
    localStorage.setItem('tree_panel_collapsed', String(treePanelCollapsed))
  }, [treePanelCollapsed])

  useEffect(() => {
    localStorage.setItem('tree_panel_width', String(treePanelWidth))
  }, [treePanelWidth])

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
    const startX = e.clientX
    const startWidth = treePanelWidth

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientX - startX
      const newWidth = Math.min(Math.max(startWidth + delta, 160), 400)
      setTreePanelWidth(newWidth)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [treePanelWidth])

  const filteredRuns = useMemo(() => {
    return runs.filter(run => {
      const searchLower = searchText.toLowerCase()
      const matchesSearch = searchText === '' ||
        run.run_id.toLowerCase().includes(searchLower) ||
        run.path.toLowerCase().includes(searchLower) ||
        (run.alias && run.alias.toLowerCase().includes(searchLower)) ||
        (run.tags && run.tags.some((tag: string) => tag.toLowerCase().includes(searchLower)))

      const matchesTreePath = !selectedTreePath ||
        run.path === selectedTreePath ||
        run.path.startsWith(`${selectedTreePath}/`)

      const topLevelPath = run.path.split('/')[0]
      const matchesProject = projectFilter === 'all' || topLevelPath === projectFilter

      const matchesStatus = statusFilter === 'all' || run.status === statusFilter

      return matchesSearch && matchesTreePath && matchesProject && matchesStatus
    })
  }, [runs, searchText, selectedTreePath, projectFilter, statusFilter])

  return {
    searchText, setSearchText,
    projectFilter, setProjectFilter,
    statusFilter, setStatusFilter,
    selectedTreePath, setSelectedTreePath,
    sortedInfo, setSortedInfo,
    pageSize, setPageSize,
    treePanelCollapsed, setTreePanelCollapsed,
    treePanelWidth, setTreePanelWidth,
    isResizing, handleResizeStart,
    filteredRuns,
  }
}
