import React, { useState } from 'react'
import { Search, AlertCircle } from 'lucide-react'
import GraphViewer from '../components/graph/GraphViewer'
import { EmptyState } from '../components/common'
import { useInvestigation } from '../contexts/InvestigationContext'

const GraphExplorer: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null)
  const investigation = useInvestigation()

  const handleSearch = () => {
    if (searchQuery.trim()) {
      setSelectedAccount(searchQuery.trim())
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Graph Explorer</h1>
        <p className="text-slate-600">
          Visualize account relationships and suspicious connections in the fraud network
        </p>
      </div>

      {/* Search and Configuration */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Search Account to Visualize
          </label>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" size={20} />
              <input
                type="text"
                placeholder="Enter account ID (e.g., FRAUD_001, SUSP_001, ACC_001)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button
              onClick={handleSearch}
              className="px-6 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Explore
            </button>
          </div>
        </div>

        {selectedAccount && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Traversal Depth: {investigation.state.graphDepth}
            </label>
            <input
              type="range"
              min="1"
              max="3"
              value={investigation.state.graphDepth}
              onChange={(e) => investigation.setGraphDepth(Number(e.target.value))}
              className="w-full"
            />
            <p className="text-xs text-slate-500 mt-2">
              Higher depth shows more connections but may be slower
            </p>
          </div>
        )}
      </div>

      {/* Graph Visualization Area */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-6">
        {!selectedAccount ? (
          <EmptyState
            icon="🔍"
            message="Select an account to explore"
            description="Enter an account ID above to visualize its relationships in the fraud network"
          />
        ) : (
          <>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-900">
                <strong>Selected Account:</strong> {selectedAccount}
              </p>
              <p className="text-sm text-blue-700 mt-2">
                Showing connections within {investigation.state.graphDepth} hop(s)
              </p>
            </div>

            {/* Interactive Graph */}
            <GraphViewer accountId={selectedAccount} />

            {/* Graph Legend */}
            <div className="bg-slate-50 rounded-lg border border-slate-200 p-4">
              <h4 className="font-semibold text-slate-900 mb-3">Legend</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="flex items-center gap-2">
                  <div
                    className="w-6 h-6 rounded"
                    style={{ backgroundColor: '#dc2626' }}
                  />
                  <span className="text-sm text-slate-700">Critical Risk</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className="w-6 h-6 rounded"
                    style={{ backgroundColor: '#ea580c' }}
                  />
                  <span className="text-sm text-slate-700">High Risk</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className="w-6 h-6 rounded"
                    style={{ backgroundColor: '#eab308' }}
                  />
                  <span className="text-sm text-slate-700">Medium Risk</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className="w-6 h-6 rounded"
                    style={{ backgroundColor: '#16a34a' }}
                  />
                  <span className="text-sm text-slate-700">Low Risk</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className="w-6 h-6 rounded"
                    style={{ backgroundColor: '#3b82f6' }}
                  />
                  <span className="text-sm text-slate-700">Card</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className="w-6 h-6 rounded"
                    style={{ backgroundColor: '#64748b' }}
                  />
                  <span className="text-sm text-slate-700">Device</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className="w-6 h-6 rounded"
                    style={{ backgroundColor: '#7c3aed' }}
                  />
                  <span className="text-sm text-slate-700">Phone</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className="w-6 h-6 rounded"
                    style={{ backgroundColor: '#0891b2' }}
                  />
                  <span className="text-sm text-slate-700">IP Address</span>
                </div>
              </div>
            </div>

            {/* Investigation Tips */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                <AlertCircle size={18} />
                Investigation Tips
              </h4>
              <ul className="text-sm text-slate-700 space-y-1">
                <li>
                  • Drag nodes to rearrange the visualization for better readability
                </li>
                <li>
                  • Use the mouse wheel or pinch to zoom in/out
                </li>
                <li>
                  • Click the fit view button (bottom right) to reset the view
                </li>
                <li>
                  • Red nodes indicate critical or known fraud accounts
                </li>
                <li>
                  • Animated edges show direct relationships from the selected account
                </li>
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default GraphExplorer
