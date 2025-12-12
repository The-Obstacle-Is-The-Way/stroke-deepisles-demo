import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { server } from './mocks/server'
import { errorHandlers } from './mocks/handlers'
import App from './App'

// Mock NiiVue to avoid WebGL in tests
vi.mock('@niivue/niivue', () => ({
  Niivue: class MockNiivue {
    attachToCanvas = vi.fn()
    loadVolumes = vi.fn().mockResolvedValue(undefined)
    cleanup = vi.fn()
    gl = {
      getExtension: vi.fn(() => ({ loseContext: vi.fn() })),
    }
    opts = {}
  },
}))

describe('App Integration', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('Initial Render', () => {
    it('renders main heading', () => {
      render(<App />)

      expect(
        screen.getByRole('heading', { name: /stroke lesion segmentation/i })
      ).toBeInTheDocument()
    })

    it('renders case selector', async () => {
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })
    })

    it('renders run button', () => {
      render(<App />)

      expect(
        screen.getByRole('button', { name: /run segmentation/i })
      ).toBeInTheDocument()
    })

    it('shows placeholder viewer message', () => {
      render(<App />)

      expect(
        screen.getByText(/select a case and run segmentation/i)
      ).toBeInTheDocument()
    })
  })

  describe('Run Button State', () => {
    it('disables run button when no case selected', async () => {
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      expect(
        screen.getByRole('button', { name: /run segmentation/i })
      ).toBeDisabled()
    })

    it('enables run button when case selected', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')

      expect(
        screen.getByRole('button', { name: /run segmentation/i })
      ).toBeEnabled()
    })
  })

  describe('Segmentation Flow', () => {
    it('shows processing state when running', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      expect(screen.getByText(/processing/i)).toBeInTheDocument()
    })

    it('shows progress indicator during job execution', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      // Progress indicator should appear
      await waitFor(() => {
        expect(screen.getByRole('progressbar')).toBeInTheDocument()
      })
    })

    it('displays metrics after successful segmentation', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      // Advance time to allow job to complete (mock jobs complete in ~3s)
      await vi.advanceTimersByTimeAsync(5000)

      await waitFor(() => {
        expect(screen.getByText('0.847')).toBeInTheDocument()
      })

      expect(screen.getByText('15.32 mL')).toBeInTheDocument()
    })

    it('displays viewer after successful segmentation', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      // Advance time to allow job to complete
      await vi.advanceTimersByTimeAsync(5000)

      await waitFor(() => {
        expect(document.querySelector('canvas')).toBeInTheDocument()
      })
    })

    it('hides placeholder after successful segmentation', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      // Advance time to allow job to complete
      await vi.advanceTimersByTimeAsync(5000)

      await waitFor(() => {
        expect(screen.getByText('0.847')).toBeInTheDocument()
      })

      expect(
        screen.queryByText(/select a case and run segmentation/i)
      ).not.toBeInTheDocument()
    })

    it('shows cancel button during processing', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('shows error when job creation fails', async () => {
      server.use(errorHandlers.segmentCreateError)
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(screen.getByText(/failed to create job/i)).toBeInTheDocument()
    })

    it('allows retry after error', async () => {
      server.use(errorHandlers.segmentCreateError)
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      // Reset to success handler
      server.resetHandlers()

      // Retry
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      // Advance time to allow job to complete
      await vi.advanceTimersByTimeAsync(5000)

      await waitFor(() => {
        expect(screen.getByText('0.847')).toBeInTheDocument()
      })

      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })

  describe('Multiple Runs', () => {
    it('allows running segmentation on different cases', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      // First case
      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      // Advance time to allow job to complete
      await vi.advanceTimersByTimeAsync(5000)

      // Wait for first segmentation to complete
      await waitFor(() => {
        expect(screen.getByText('sub-stroke0001')).toBeInTheDocument()
      })

      // Wait for button to be ready again (not "Processing...")
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /run segmentation/i })).toBeInTheDocument()
      })

      // Second case
      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0002')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      // Advance time to allow second job to complete
      await vi.advanceTimersByTimeAsync(5000)

      await waitFor(() => {
        expect(screen.getByText('sub-stroke0002')).toBeInTheDocument()
      })
    })
  })
})
