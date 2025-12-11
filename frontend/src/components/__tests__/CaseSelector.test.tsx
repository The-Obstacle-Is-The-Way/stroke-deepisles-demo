import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { server } from '../../mocks/server'
import { errorHandlers } from '../../mocks/handlers'
import { CaseSelector } from '../CaseSelector'

describe('CaseSelector', () => {
  const mockOnSelectCase = vi.fn()

  beforeEach(() => {
    mockOnSelectCase.mockClear()
  })

  it('shows loading state initially', () => {
    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('renders select after loading', async () => {
    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })
  })

  it('displays all cases as options', async () => {
    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    expect(screen.getByRole('option', { name: /sub-stroke0001/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /sub-stroke0002/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /sub-stroke0003/i })).toBeInTheDocument()
  })

  it('has placeholder option', async () => {
    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    expect(screen.getByRole('option', { name: /choose a case/i })).toBeInTheDocument()
  })

  it('calls onSelectCase when case selected', async () => {
    const user = userEvent.setup()

    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')

    expect(mockOnSelectCase).toHaveBeenCalledWith('sub-stroke0001')
  })

  it('shows selected case value', async () => {
    render(
      <CaseSelector
        selectedCase="sub-stroke0002"
        onSelectCase={mockOnSelectCase}
      />
    )

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toHaveValue('sub-stroke0002')
    })
  })

  it('shows error state on API failure', async () => {
    server.use(errorHandlers.casesServerError)

    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
    })
  })

  it('applies correct styling', async () => {
    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    const container = screen.getByRole('combobox').closest('div')
    expect(container).toHaveClass('bg-gray-800')
  })
})
