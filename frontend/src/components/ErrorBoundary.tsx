import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import Icon from './Icon';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('Error caught by ErrorBoundary:', error, errorInfo);
    
    // Log to error tracking service if available
    if (typeof window !== 'undefined' && (window as any).trackError) {
      (window as any).trackError(error, errorInfo);
    }
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-main)] p-4">
          <div className="max-w-md w-full bg-[var(--color-bg-card)] rounded-xl shadow-lg border border-[var(--color-border-light)] p-8">
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 bg-[var(--color-error-50)] rounded-full flex items-center justify-center mb-4">
                <Icon as={AlertCircle} size={32} className="text-[var(--color-error-600)]" />
              </div>
              
              <h1 className="text-2xl font-bold text-[var(--color-text-primary)] mb-2">
                Something went wrong
              </h1>
              
              <p className="text-[var(--color-text-secondary)] mb-6">
                {this.state.error?.message || 'An unexpected error occurred'}
              </p>

              <div className="space-y-3 w-full">
                <button
                  onClick={this.handleReset}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[var(--color-primary-600)] text-white rounded-lg hover:bg-[var(--color-primary-700)] transition-colors"
                >
                  <Icon as={RefreshCw} size={18} />
                  Try again
                </button>
                
                <button
                  onClick={() => window.location.href = '/'}
                  className="w-full px-4 py-3 border border-[var(--color-border-medium)] text-[var(--color-text-secondary)] rounded-lg hover:bg-[var(--color-bg-hover)] transition-colors"
                >
                  Go to home
                </button>
              </div>

              {process.env.NODE_ENV === 'development' && this.state.error && (
                <details className="mt-6 text-left w-full">
                  <summary className="cursor-pointer text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]">
                    Error details
                  </summary>
                  <pre className="mt-2 p-3 bg-[var(--color-bg-subtle)] rounded-lg text-xs text-[var(--color-error-600)] overflow-auto max-h-48">
                    {this.state.error.toString()}
                    {'\n\n'}
                    {this.state.error.stack}
                  </pre>
                </details>
              )}
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
