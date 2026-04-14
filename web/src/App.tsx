import { Component, ErrorInfo, ReactNode } from 'react';
import { Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { cn } from './lib/utils';

// Layout
import Sidebar from './components/layout/Sidebar';

// Pages
import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import Register from './pages/Register';
import Overview from './pages/Overview';
import NewDiscussion from './pages/NewDiscussion';
import Discussion from './pages/Discussion';
import HistoryPage from './pages/History';
import Personas from './pages/Personas';
import Assets from './pages/Assets';
import Teams from './pages/Teams';
import Settings from './pages/Settings';
import Features from './pages/Features';

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 bg-red-900 text-white min-h-screen">
          <h1 className="text-2xl font-bold mb-4">Something went wrong.</h1>
          <pre className="bg-black/50 p-4 rounded overflow-auto">
            {this.state.error?.toString()}
            {'\n\n'}
            {this.state.error?.stack}
          </pre>
        </div>
      );
    }

    return this.props.children;
  }
}

// Pages that do NOT show the sidebar
const NO_SIDEBAR_PATHS = ['/', '/login', '/register', '/features'];

export default function App() {
  const location = useLocation();
  const showSidebar = !NO_SIDEBAR_PATHS.includes(location.pathname);

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-[#0b0f17] text-white flex overflow-hidden font-sans">
        {showSidebar && <Sidebar />}

        <main
          className={cn(
            'flex-1 flex flex-col h-screen overflow-hidden relative bg-[#0b0f17]',
            !showSidebar && 'w-full'
          )}
        >
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/features" element={<Features />} />

            {/* App routes */}
            <Route path="/app" element={<Overview />} />
            <Route path="/app/new" element={<NewDiscussion />} />
            <Route path="/app/discussion/:id" element={<Discussion />} />
            <Route path="/app/history" element={<HistoryPage />} />
            <Route path="/app/personas" element={<Personas />} />
            <Route path="/app/assets" element={<Assets />} />
            <Route path="/app/teams" element={<Teams />} />
            <Route path="/app/settings" element={<Settings />} />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </ErrorBoundary>
  );
}
