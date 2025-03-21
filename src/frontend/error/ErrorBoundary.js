import React from 'react';
import { loggerService } from '../services/logger';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    
    // エラー情報をバックエンドに送信
    loggerService.logError(error, {
      componentStack: errorInfo.componentStack,
      componentName: this.props.componentName || 'Unknown'
    });
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || <h2>エラーが発生しました。開発チームに報告されました。</h2>;
    }
    return this.props.children;
  }
}

export default ErrorBoundary; 