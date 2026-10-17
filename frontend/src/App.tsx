import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Landing from './pages/Landing';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import UserProfile from './pages/UserProfile';
import Onboarding from './pages/Onboarding';
import Legal from './pages/Legal';
import ErrorBoundary from './components/ErrorBoundary';

const Dashboard = lazy(() => import('./pages/Dashboard'));

function App() {
  return (
    <Router>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'rgba(30, 27, 46, 0.95)',
            color: '#e2e0ef',
            border: '1px solid rgba(255,255,255,0.08)',
            backdropFilter: 'blur(12px)',
          },
        }}
      />
      <Routes>
        <Route path="/" element={<ErrorBoundary><Landing /></ErrorBoundary>} />
        <Route path="/login" element={<ErrorBoundary><Login /></ErrorBoundary>} />
        <Route path="/callback" element={<ErrorBoundary><AuthCallback /></ErrorBoundary>} />
        <Route path="/onboarding" element={<ErrorBoundary><Onboarding /></ErrorBoundary>} />
        <Route path="/dashboard" element={
          <ErrorBoundary>
            <Suspense fallback={<p role="status" className="p-8 text-center text-nexus-textMuted">Loading dashboard…</p>}>
              <Dashboard />
            </Suspense>
          </ErrorBoundary>
        } />
        <Route path="/profile" element={<ErrorBoundary><UserProfile /></ErrorBoundary>} />
        <Route path="/privacy" element={<ErrorBoundary><Legal doc="privacy" /></ErrorBoundary>} />
        <Route path="/terms" element={<ErrorBoundary><Legal doc="terms" /></ErrorBoundary>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
