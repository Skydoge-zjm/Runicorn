import { useState, useEffect, useCallback } from 'react'
import { debounce } from 'lodash'

interface ColumnWidths {
  [key: string]: number
}

interface WindowSizeKey {
  width: number
  height: number
}

// Get window size category for grouping similar sizes
const getWindowSizeCategory = (width: number, height: number): string => {
  // Round to nearest 100px to group similar window sizes
  const roundedWidth = Math.round(width / 100) * 100
  const roundedHeight = Math.round(height / 100) * 100
  return `${roundedWidth}x${roundedHeight}`
}

/**
 * Hook for managing resizable column widths with persistence
 * Stores different column width preferences for different window sizes
 */
export function useColumnWidths(
  tableKey: string,
  defaultWidths: ColumnWidths
): {
  columnWidths: ColumnWidths
  setColumnWidth: (columnKey: string, width: number) => void
  resetWidths: () => void
} {
  const [columnWidths, setColumnWidths] = useState<ColumnWidths>(defaultWidths)
  const [windowSize, setWindowSize] = useState({ 
    width: window.innerWidth, 
    height: window.innerHeight 
  })

  // Load saved preferences for current window size
  useEffect(() => {
    loadPreferences()
  }, [windowSize, tableKey])

  // Handle window resize
  useEffect(() => {
    const handleResize = debounce(() => {
      setWindowSize({ width: window.innerWidth, height: window.innerHeight })
    }, 300)

    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      handleResize.cancel()
    }
  }, [])

  const loadPreferences = async () => {
    try {
      const sizeKey = getWindowSizeCategory(windowSize.width, windowSize.height)
      const response = await fetch(`/api/config/column-widths?table=${tableKey}&size=${sizeKey}`)
      
      if (response.ok) {
        const data = await response.json()
        if (data.widths) {
          setColumnWidths({ ...defaultWidths, ...data.widths })
        }
      }
    } catch (error) {
      console.warn('Failed to load column width preferences:', error)
    }
  }

  const savePreferences = useCallback(
    debounce(async (widths: ColumnWidths) => {
      try {
        const sizeKey = getWindowSizeCategory(windowSize.width, windowSize.height)
        await fetch('/api/config/column-widths', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            table: tableKey,
            size: sizeKey,
            widths: widths,
            window_width: windowSize.width,
            window_height: windowSize.height
          })
        })
      } catch (error) {
        console.warn('Failed to save column width preferences:', error)
      }
    }, 1000),
    [tableKey, windowSize]
  )

  const setColumnWidth = useCallback((columnKey: string, width: number) => {
    setColumnWidths(prev => {
      const newWidths = { ...prev, [columnKey]: width }
      savePreferences(newWidths)
      return newWidths
    })
  }, [savePreferences])

  const resetWidths = useCallback(() => {
    setColumnWidths(defaultWidths)
    savePreferences(defaultWidths)
  }, [defaultWidths, savePreferences])

  return {
    columnWidths,
    setColumnWidth,
    resetWidths
  }
}

