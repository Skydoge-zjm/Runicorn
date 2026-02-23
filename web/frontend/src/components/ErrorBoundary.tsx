import React from 'react'
import { Alert, Button } from 'antd'

interface Props {
  children: React.ReactNode
  fallback?: string
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <Alert
          type="error"
          message={this.props.fallback || 'Component Error'}
          description={this.state.error?.message}
          action={
            <Button size="small" onClick={() => this.setState({ hasError: false })}>
              Retry
            </Button>
          }
        />
      )
    }
    return this.props.children
  }
}

export default ErrorBoundary
