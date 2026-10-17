import React, { Component } from 'react';
import type { ReactNode } from 'react';

interface Props {
  children: ReactNode;
  /** What failed, shown in the fallback, e.g. "the inbox". */
  name?: string;
}

interface State {
  hasError: boolean;
}

class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // TODO: Replace with error reporting service
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div role="alert" className="m-4 p-6 rounded-xl border border-nexus-border bg-nexus-card text-center flex flex-col items-center gap-3">
          <h2 className="text-lg font-semibold text-nexus-text">Something went wrong{this.props.name ? ` in ${this.props.name}` : ''}.</h2>
          <p className="text-sm text-nexus-textMuted">The rest of the app still works. You can try again, or reload the page if the problem continues.</p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => this.setState({ hasError: false })}
              className="px-4 py-2 rounded-lg bg-nexus-primary text-black text-sm font-medium"
            >
              Try again
            </button>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-lg border border-nexus-border text-nexus-text text-sm"
            >
              Reload page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
