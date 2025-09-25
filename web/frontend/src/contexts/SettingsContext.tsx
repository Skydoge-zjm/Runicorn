import React, { createContext, useContext } from 'react'
import type { UiSettings } from '../components/SettingsDrawer'

interface SettingsContextType {
  settings: UiSettings
  setSettings: (settings: UiSettings) => void
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

export const SettingsProvider: React.FC<{ 
  children: React.ReactNode
  value: SettingsContextType
}> = ({ children, value }) => (
  <SettingsContext.Provider value={value}>
    {children}
  </SettingsContext.Provider>
)

export const useSettings = (): SettingsContextType => {
  const context = useContext(SettingsContext)
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider')
  }
  return context
}
