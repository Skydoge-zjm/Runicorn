export type DiagnosticsSourceKind = 'session' | 'global' | 'viewer' | 'bootstrap'

export interface DiagnosticsSource {
  id: string
  kind: DiagnosticsSourceKind
  path: string
  available: boolean
}

export interface DiagnosticsSourcesResponse {
  remoteMode: boolean
  appSessionId: string
  defaultSource: string
  sources: DiagnosticsSource[]
}
