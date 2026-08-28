import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  BarChart3,
  Users,
  Network,
  LogIn,
  Eye,
  Menu,
  X,
  AlertCircle,
} from 'lucide-react'

const navItems = [
  { label: 'Dashboard', route: '/', icon: BarChart3 },
  { label: 'Accounts', route: '/accounts', icon: Users },
  { label: 'Fraud Rings', route: '/fraud-rings', icon: Network },
  { label: 'Transactions', route: '/transactions', icon: LogIn },
  { label: 'Graph Explorer', route: '/graph', icon: Eye },
]

export const Sidebar: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
  const location = useLocation()

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed left-0 top-0 h-screen w-64 bg-slate-900 text-slate-100 z-50
          transform transition-transform duration-200 ease-in-out
          lg:static lg:translate-x-0
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="flex items-center justify-between h-16 px-6 border-b border-slate-700">
          <Link to="/" className="flex items-center gap-2 font-bold text-lg hover:text-blue-400 transition-colors">
            <AlertCircle size={24} className="text-blue-400" />
            <span>Fraud Detection</span>
          </Link>
          <button onClick={onClose} className="lg:hidden text-slate-400 hover:text-white">
            <X size={20} />
          </button>
        </div>

        <nav className="px-4 py-6 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.route
            return (
              <Link
                key={item.route}
                to={item.route}
                onClick={onClose}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg transition-all
                  ${isActive
                    ? 'bg-blue-600 text-white font-medium'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }
                `}
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>

        <div className="absolute bottom-6 left-6 right-6 p-4 bg-slate-800 rounded-lg border border-slate-700">
          <p className="text-xs text-slate-400">Demo Mode</p>
          <p className="text-sm font-medium text-slate-200 mt-1">Fraud Detection System</p>
        </div>
      </aside>
    </>
  )
}

export const Header: React.FC<{ onMenuClick: () => void }> = ({ onMenuClick }) => {
  const location = useLocation()

  const getPageTitle = () => {
    const item = navItems.find((n) => n.route === location.pathname)
    return item?.label || 'Dashboard'
  }

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
      <div className="flex items-center justify-between h-16 px-6">
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 hover:bg-slate-100 rounded-lg text-slate-600"
          >
            <Menu size={24} />
          </button>
          <h1 className="text-xl font-bold text-slate-900">{getPageTitle()}</h1>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-full border border-blue-200">
            <div className="w-2 h-2 bg-green-500 rounded-full" />
            <span className="text-xs font-medium text-blue-700">Connected</span>
          </div>
        </div>
      </div>
    </header>
  )
}

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
        <main className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">{children}</div>
        </main>
      </div>
    </div>
  )
}
