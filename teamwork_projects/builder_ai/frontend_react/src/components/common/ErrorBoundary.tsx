import React, { Component, ErrorInfo, ReactNode } from 'react';
import { RefreshCw, AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="w-full h-full min-h-[300px] flex flex-col items-center justify-center p-8 text-center bg-[#08090B] text-white">
          <div className="w-12 h-12 rounded-2xl bg-[#FF4E4E]/15 flex items-center justify-center mb-4 text-[#FF4E4E]">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-black tracking-tight mb-2">
            {this.props.fallbackTitle || 'Rendering System Notice'}
          </h2>
          <p className="text-xs text-[#8E8F9C] max-w-md mb-6 leading-relaxed">
            {this.state.error?.message || 'An unexpected rendering anomaly was safely contained. You can restore the 3D workspace with one click.'}
          </p>
          <button
            onClick={this.handleReset}
            className="flex items-center gap-2 px-6 py-2.5 rounded-full bg-[#D4FF32] text-black font-extrabold text-xs shadow-lg hover:scale-105 transition-transform"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Restore Studio</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
