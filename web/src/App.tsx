import { Component, ErrorInfo, ReactNode } from 'react';
import { Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react';
import { cn } from './lib/utils';
import { CLERK_ENABLED } from './lib/runtime';

// Layout
import Sidebar from './components/layout/Sidebar';

// Pages
import Overview from './pages/Overview';
import NewDiscussion from './pages/NewDiscussion';
import Discussion from './pages/Discussion';
import HistoryPage from './pages/History';
import Personas from './pages/Personas';
import Assets from './pages/Assets';
import Teams from './pages/Teams';
import Settings from './pages/Settings';
import SignInPage from './pages/SignInPage';
import SignUpPage from './pages/SignUpPage';
// PRICING_V2 (disabled for MVP):
// import Billing from './pages/Billing';

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
const NO_SIDEBAR_PATHS = ['/sign-in', '/sign-up'];

/** Wraps a route element: in Clerk mode, redirects unauthenticated users to sign-in. */
function Protected({ children }: { children: React.ReactNode }) {
  if (!CLERK_ENABLED) return <>{children}</>;
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <RedirectToSignIn />
      </SignedOut>
    </>
  );
}

export default function App() {
  const location = useLocation();
  const showSidebar = !NO_SIDEBAR_PATHS.some((p) =>
    location.pathname === p || location.pathname.startsWith(p + '/')
  );

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
            {/* Auth pages — Clerk hosted UI */}
            <Route path="/sign-in/*" element={<SignInPage />} />
            <Route path="/sign-up/*" element={<SignUpPage />} />

            {/* App routes — protected when Clerk is enabled */}
            <Route path="/" element={<Protected><Overview /></Protected>} />
            <Route path="/new" element={<Protected><NewDiscussion /></Protected>} />
            <Route path="/discussion/:id" element={<Protected><Discussion /></Protected>} />
            <Route path="/history" element={<Protected><HistoryPage /></Protected>} />
            <Route path="/personas" element={<Protected><Personas /></Protected>} />
            <Route path="/assets" element={<Protected><Assets /></Protected>} />
            <Route path="/teams" element={<Protected><Teams /></Protected>} />
            <Route path="/settings" element={<Protected><Settings /></Protected>} />
            {/* PRICING_V2 (disabled for MVP):
                <Route path="/billing" element={<Protected><Billing /></Protected>} />
            */}

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </ErrorBoundary>
  );
}
