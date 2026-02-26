import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StatusTag from './StatusTag'

describe('StatusTag', () => {
  it('renders "Running" with processing color', () => {
    render(<StatusTag status="running" />)
    const tag = screen.getByText('Running')
    expect(tag).toBeInTheDocument()
    expect(tag.closest('.ant-tag')).toHaveClass('ant-tag-processing')
  })

  it('renders "Finished" with success color', () => {
    render(<StatusTag status="finished" />)
    const tag = screen.getByText('Finished')
    expect(tag).toBeInTheDocument()
    expect(tag.closest('.ant-tag')).toHaveClass('ant-tag-success')
  })

  it('renders "Failed" with error color', () => {
    render(<StatusTag status="failed" />)
    const tag = screen.getByText('Failed')
    expect(tag).toBeInTheDocument()
    expect(tag.closest('.ant-tag')).toHaveClass('ant-tag-error')
  })

  it('renders unknown status with default tag', () => {
    render(<StatusTag status="unknown" />)
    const tag = screen.getByText('Unknown')
    expect(tag).toBeInTheDocument()
    // Default tag has no color class
    expect(tag.closest('.ant-tag')).not.toHaveClass('ant-tag-processing')
    expect(tag.closest('.ant-tag')).not.toHaveClass('ant-tag-success')
    expect(tag.closest('.ant-tag')).not.toHaveClass('ant-tag-error')
  })
})
