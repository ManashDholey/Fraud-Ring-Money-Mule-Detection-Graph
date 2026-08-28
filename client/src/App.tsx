import { Suspense, lazy } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { InvestigationProvider } from './contexts/InvestigationContext'
import { LoadingSkeleton } from './components/common'

// Lazy load all route components for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Accounts = lazy(() => import('./pages/Accounts'))
const AccountDetail = lazy(() => import('./pages/AccountDetail'))
const FraudRings = lazy(() => import('./pages/FraudRings'))
const Transactions = lazy(() => import('./pages/Transactions'))
const GraphExplorer = lazy(() => import('./pages/GraphExplorer'))

// Loading component shown while route component loads
const RouteLoader = () => <LoadingSkeleton rows={5} columns={3} />

export default function App() {
  return (
    <InvestigationProvider>
      <Router>
        <Layout>
          <Suspense fallback={<RouteLoader />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/accounts" element={<Accounts />} />
              <Route path="/accounts/:id" element={<AccountDetail />} />
              <Route path="/fraud-rings" element={<FraudRings />} />
              <Route path="/transactions" element={<Transactions />} />
              <Route path="/graph" element={<GraphExplorer />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </Layout>
      </Router>
    </InvestigationProvider>
  )
}
