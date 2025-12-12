import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

/**
 * Error Boundary component to catch React rendering errors.
 *
 * Prevents the entire app from crashing when a component throws.
 * Displays a user-friendly error message instead of a white screen.
 *
 * Usage:
 *   <ErrorBoundary>
 *     <ComponentThatMightThrow />
 *   </ErrorBoundary>
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error for debugging
    console.error('ErrorBoundary caught error:', error, errorInfo)
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null })
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
          <div className="bg-gray-800 rounded-lg p-6 max-w-md w-full text-center space-y-4">
            <div className="text-red-400 text-4xl">Something went wrong</div>
            <p className="text-gray-300">
              An unexpected error occurred while rendering the application.
            </p>
            {this.state.error && (
              <details className="text-left">
                <summary className="text-gray-400 cursor-pointer hover:text-gray-300">
                  Error details
                </summary>
                <pre className="mt-2 p-2 bg-gray-900 rounded text-xs text-red-300 overflow-auto max-h-32">
                  {this.state.error.message}
                </pre>
              </details>
            )}
            <button
              onClick={this.handleRetry}
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
