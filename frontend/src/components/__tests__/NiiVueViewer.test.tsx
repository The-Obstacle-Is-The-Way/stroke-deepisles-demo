import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { NiiVueViewer } from '../NiiVueViewer'

// Store mock function references so tests can verify calls
const mockLoadVolumes = vi.fn().mockResolvedValue(undefined)
const mockCleanup = vi.fn()
const mockAttachToCanvas = vi.fn()
const mockLoseContext = vi.fn()

// Mock the NiiVue module since it requires actual WebGL
vi.mock('@niivue/niivue', () => ({
  Niivue: class MockNiivue {
    attachToCanvas = mockAttachToCanvas
    loadVolumes = mockLoadVolumes
    setSliceType = vi.fn()
    cleanup = mockCleanup
    gl = {
      getExtension: vi.fn(() => ({ loseContext: mockLoseContext })),
    }
    opts = {}
  },
}))

describe('NiiVueViewer', () => {
  const defaultProps = {
    backgroundUrl: 'http://localhost:7860/files/dwi.nii.gz',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders canvas element', () => {
    render(<NiiVueViewer {...defaultProps} />)

    expect(document.querySelector('canvas')).toBeInTheDocument()
  })

  it('renders container with correct styling', () => {
    render(<NiiVueViewer {...defaultProps} />)

    const container = document.querySelector('canvas')?.parentElement
    expect(container).toHaveClass('bg-gray-900')
  })

  it('renders help text for controls', () => {
    render(<NiiVueViewer {...defaultProps} />)

    expect(screen.getByText(/scroll/i)).toBeInTheDocument()
    expect(screen.getByText(/drag/i)).toBeInTheDocument()
  })

  it('attaches NiiVue to canvas on mount', () => {
    render(<NiiVueViewer {...defaultProps} />)

    expect(mockAttachToCanvas).toHaveBeenCalled()
    // Verify it was called with a canvas element
    const arg = mockAttachToCanvas.mock.calls[0][0]
    expect(arg).toBeInstanceOf(HTMLCanvasElement)
  })

  it('loads background volume on mount', () => {
    render(<NiiVueViewer {...defaultProps} />)

    expect(mockLoadVolumes).toHaveBeenCalledWith([
      { url: defaultProps.backgroundUrl, colormap: 'gray', opacity: 1 },
    ])
  })

  it('loads both background and overlay when overlayUrl provided', () => {
    const overlayUrl = 'http://localhost:7860/files/prediction.nii.gz'

    render(
      <NiiVueViewer
        {...defaultProps}
        overlayUrl={overlayUrl}
      />
    )

    expect(mockLoadVolumes).toHaveBeenCalledWith([
      { url: defaultProps.backgroundUrl, colormap: 'gray', opacity: 1 },
      { url: overlayUrl, colormap: 'red', opacity: 0.5 },
    ])
  })

  it('calls cleanup on unmount', () => {
    const { unmount } = render(<NiiVueViewer {...defaultProps} />)

    unmount()

    expect(mockCleanup).toHaveBeenCalled()
    expect(mockLoseContext).toHaveBeenCalled()
  })

  it('sets canvas dimensions', () => {
    render(<NiiVueViewer {...defaultProps} />)

    const canvas = document.querySelector('canvas')
    expect(canvas).toHaveClass('w-full', 'h-[500px]')
  })

  it('displays error when volume loading fails', async () => {
    const errorMessage = 'Network error loading volume'
    mockLoadVolumes.mockRejectedValueOnce(new Error(errorMessage))

    render(<NiiVueViewer {...defaultProps} />)

    // Wait for error to be displayed
    const errorElement = await screen.findByText(/failed to load volume/i)
    expect(errorElement).toBeInTheDocument()
    expect(errorElement).toHaveTextContent(errorMessage)
  })

  it('calls onError callback when volume loading fails', async () => {
    const errorMessage = 'Network error'
    const onError = vi.fn()
    mockLoadVolumes.mockRejectedValueOnce(new Error(errorMessage))

    render(<NiiVueViewer {...defaultProps} onError={onError} />)

    // Wait for error callback to be invoked (use RTL's waitFor, not vi.waitFor)
    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(errorMessage)
    })
  })

  it('ignores errors from stale loads after URL change', async () => {
    const onError = vi.fn()
    // First load succeeds, second load fails slowly
    let rejectSecondLoad: (error: Error) => void
    mockLoadVolumes
      .mockResolvedValueOnce(undefined)
      .mockImplementationOnce(() => new Promise((_, reject) => {
        rejectSecondLoad = reject
      }))

    const { rerender } = render(
      <NiiVueViewer backgroundUrl="http://localhost/first.nii.gz" onError={onError} />
    )

    // Change URL - starts second load
    rerender(
      <NiiVueViewer backgroundUrl="http://localhost/second.nii.gz" onError={onError} />
    )

    // Change URL again - makes second load stale
    rerender(
      <NiiVueViewer backgroundUrl="http://localhost/third.nii.gz" onError={onError} />
    )

    // Now reject the second load (stale)
    rejectSecondLoad!(new Error('Stale load error'))

    // Flush async work (let rejection be processed) before asserting
    // Using waitFor with negative assertions is flaky - it passes immediately
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(onError).not.toHaveBeenCalledWith('Stale load error')
  })
})
