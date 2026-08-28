import React, { useCallback, useMemo, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { useAccountPagination } from '../hooks/useAccountPagination'
import { useInfiniteScroll } from '../hooks/useInfiniteScroll'
import { useInvestigation } from '../contexts/InvestigationContext'
import { RiskBadge, EmptyState, ErrorState, LoadingSkeleton, StatusBadge } from '../components/common'
import type { AccountDTO } from '../types/api'

const DEBOUNCE_DELAY = 300

const Accounts: React.FC = () => {
  const navigate = useNavigate()
  const investigation = useInvestigation()
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [debouncedQuery, setDebouncedQuery] = React.useState('')

  // Debounce search input
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedQuery(investigation.state.accountSearch)
    }, DEBOUNCE_DELAY)

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [investigation.state.accountSearch])

  const filters = useMemo(
    () => ({
      query: debouncedQuery,
      riskLevel: investigation.state.riskFilter ?? undefined,
      knownFraud: undefined,
    }),
    [debouncedQuery, investigation.state.riskFilter]
  )

  const { items, isLoading, isLoadingMore, hasNextPage, error, loadMore } = useAccountPagination(filters)
  // FIX: Ensure hook is called with fresh logic
  console.log('Accounts items:', items) // Debugging line to check the fetched items
  const { sentinelRef } = useInfiniteScroll(loadMore, { enabled: hasNextPage && !isLoadingMore })

  const handleSearchChange = useCallback(
    (query: string) => {
      investigation.setAccountSearch(query)
    },
    [investigation]
  )

  const handleAccountClick = useCallback(
    (accountId: string) => {
      investigation.selectAccount(accountId)
      navigate(`/accounts/${accountId}`)
    },
    [investigation, navigate]
  )

  if (error && items.length === 0) {
    return (
      <ErrorState
        title="Failed to Load Accounts"
        message={error.message}
        onRetry={() => setDebouncedQuery(debouncedQuery)}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Account Explorer</h1>
        <p className="text-slate-600">
          Search and filter suspicious accounts to begin investigation
        </p>
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" size={20} />
          <input
            type="text"
            placeholder="Search by account name or ID..."
            value={investigation.state.accountSearch}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Results */}
      {isLoading && !items.length ? (
        <LoadingSkeleton rows={5} columns={6} />
      ) : items.length === 0 && !isLoadingMore ? (
        <EmptyState icon="🔍" message="No accounts found" description="Try adjusting your search" />
      ) : (
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                    Account
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                    Customer
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                    Risk Level
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                    Known Fraud
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {items.map((account: AccountDTO) => (
                  <tr
                    key={account.accountId}
                    onClick={() => handleAccountClick(account.accountId)}
                    className="hover:bg-slate-50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">
                      {account.accountId}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                      {account.displayName}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <RiskBadge level={account.riskLevel} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <StatusBadge status={account.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {account.isKnownFraud ? (
                        <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-xs font-medium">
                          YES
                        </span>
                      ) : (
                        <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                          NO
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleAccountClick(account.accountId)
                        }}
                        className="text-blue-600 hover:text-blue-900 font-medium"
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Loading More Indicator */}
          {isLoadingMore && (
            <div className="p-4 border-t border-slate-200 text-center">
              <div className="inline-flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
                <span className="text-sm text-slate-600">Loading more...</span>
              </div>
            </div>
          )}

          {/* Infinite Scroll Sentinel */}
          {hasNextPage && <div ref={sentinelRef} className="p-4" />}

          {/* Explicit Load More Button */}
          {hasNextPage && !isLoadingMore && (
            <div className="p-4 border-t border-slate-200 text-center">
              <button
                onClick={() => loadMore()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                Load More
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Accounts
