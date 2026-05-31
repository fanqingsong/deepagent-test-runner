/**
 * ErrorBoundary Component
 *
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI.
 * WCAG 2.1 Level AA compliant with accessible error messaging.
 */

import { Component } from 'react';
import PropTypes from 'prop-types';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error to console and state
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      return (
        <div
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
          style={{
            padding: '48px',
            maxWidth: '600px',
            margin: '48px auto',
            textAlign: 'center',
            backgroundColor: '#f4f4f4',
            border: '1px solid #da1e28',
            borderRadius: '0px',
          }}
        >
          <h1
            style={{
              fontSize: '32px',
              fontWeight: '600',
              marginBottom: '16px',
              color: '#161616',
            }}
          >
            Something went wrong
          </h1>
          <p
            style={{
              fontSize: '16px',
              lineHeight: '1.5',
              marginBottom: '24px',
              color: '#525252',
            }}
          >
            We apologize for the inconvenience. An unexpected error has occurred.
            Please try refreshing the page or contact support if the problem persists.
          </p>
          <div
            style={{
              display: 'flex',
              gap: '16px',
              justifyContent: 'center',
              marginBottom: '24px',
            }}
          >
            <button
              onClick={this.handleReset}
              style={{
                padding: '12px 32px',
                fontSize: '16px',
                fontWeight: '400',
                backgroundColor: '#0f62fe',
                color: '#ffffff',
                border: 'none',
                borderRadius: '0px',
                cursor: 'pointer',
                minHeight: '48px',
              }}
              type="button"
            >
              Try Again
            </button>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: '12px 32px',
                fontSize: '16px',
                fontWeight: '400',
                backgroundColor: '#ffffff',
                color: '#0f62fe',
                border: '1px solid #0f62fe',
                borderRadius: '0px',
                cursor: 'pointer',
                minHeight: '48px',
              }}
              type="button"
            >
              Refresh Page
            </button>
          </div>
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details
              style={{
                textAlign: 'left',
                marginTop: '24px',
                padding: '16px',
                backgroundColor: '#ffffff',
                border: '1px solid #e0e0e0',
                borderRadius: '0px',
              }}
            >
              <summary
                style={{
                  cursor: 'pointer',
                  fontSize: '16px',
                  fontWeight: '600',
                  marginBottom: '8px',
                  color: '#161616',
                }}
              >
                Error Details (Development Only)
              </summary>
              <pre
                style={{
                  fontSize: '14px',
                  overflow: 'auto',
                  color: '#525252',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {this.state.error && this.state.error.toString()}
                <br />
                <br />
                {this.state.errorInfo && this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
};

export default ErrorBoundary;
