import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ErrorBoundary } from './ErrorBoundary'

// Suppress React error boundary console.error noise
const originalError = console.error
beforeEach(() => {
  console.error = vi.fn()
})
afterEach(() => {
  console.error = originalError
})

function ThrowingComponent({ message }: { message: string }) {
  throw new Error(message)
}

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Hello World</div>
      </ErrorBoundary>,
    )
    expect(screen.getByText('Hello World')).toBeInTheDocument()
  })

  it('renders fallback when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent message="Boom" />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Component Error')).toBeInTheDocument()
    expect(screen.getByText('Boom')).toBeInTheDocument()
  })

  it('renders custom fallback string', () => {
    render(
      <ErrorBoundary fallback="Custom Error Message">
        <ThrowingComponent message="Oops" />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Custom Error Message')).toBeInTheDocument()
  })
})
