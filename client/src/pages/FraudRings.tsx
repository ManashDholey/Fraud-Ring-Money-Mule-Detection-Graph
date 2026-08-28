import React, { useState } from 'react'
import { AlertCircle, Users, ChevronDown } from 'lucide-react'
import { useFraudRings } from '../hooks/useFraudRings'
import { useInfiniteScroll } from '../hooks/useInfiniteScroll'
import { RiskBadge, EmptyState, ErrorState, LoadingSkeleton } from '../components/common'
import { maskAccountNumber } from '../utils/formatting'
import type { FraudRingDTO } from '../types/api'

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const

const FraudRings: React.FC = () => {
  const [pageSize, setPageSize] = useState<number>(25)
  const { items: rings, isLoading, isLoadingMore, hasNextPage, error, loadMore, reset } = useFraudRings(pageSize)
  const { sentinelRef } = useInfiniteScroll(loadMore, { enabled: hasNextPage && !isLoadingMore })
  
  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize)
    reset()
  }

  if (error && rings.length === 0) {
    return (
      <ErrorState
        title="Failed to Load Fraud Rings"
        message={error.message}
        onRetry={() => window.location.reload()}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Fraud Rings</h1>
        <p className="text-slate-600">
          Suspicious clusters of accounts connected through shared identities and transactions
        </p>
      </div>

      {/* Pagination Controls */}
      {rings.length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-sm text-slate-600">
            Showing <span className="font-semibold">{rings.length}</span> fraud ring(s)
            {hasNextPage && ' (more available)'}
          </div>
          <div className="flex items-center gap-3">
            <label htmlFor="pageSize" className="text-sm font-medium text-slate-700">Items per page:</label>
            <div className="relative">
              <select
                id="pageSize"
                value={pageSize}
                onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                className="appearance-none px-4 py-2 pr-8 border border-slate-300 rounded-lg bg-white text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent cursor-pointer"
              >
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 text-slate-400 pointer-events-none" size={16} />
            </div>
          </div>
        </div>
      )}

      {/* Fraud Rings List */}
      {isLoading && rings.length === 0 ? (
        <LoadingSkeleton rows={4} columns={5} />
      ) : rings.length === 0 && !isLoadingMore ? (
        <EmptyState icon="🔗" message="No fraud rings detected" />
      ) : (
        <>
          <div className="space-y-4">
            {rings.map((ring: FraudRingDTO) => (
            <div
              key={ring.ringId}
              className="bg-white rounded-lg border border-slate-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-4">
                <div className="min-w-0">
                  <p className="text-sm text-slate-600 font-medium mb-1">Ring ID</p>
                  <p className="text-lg font-bold text-slate-900 truncate">{ring.ringId}</p>
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-slate-600 font-medium mb-1">Ring Size</p>
                  <p className="text-lg font-bold text-slate-900 flex items-center gap-2">
                    <Users size={20} className="flex-shrink-0" />
                    <span className="truncate">{ring.memberCount} members</span>
                  </p>
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-slate-600 font-medium mb-1">Risk Level</p>
                  <RiskBadge level={ring.riskLevel} size="md" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-slate-600 font-medium mb-1">Risk Score</p>
                  <p className="text-lg font-bold text-slate-900">{ring.riskScore.toFixed(1)}</p>
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-slate-600 font-medium mb-1">Known Fraud Count</p>
                  <p className="text-lg font-bold text-red-700">
                    {ring.knownFraudCount}
                  </p>
                </div>
              </div>

              {/* Members List */}
              <div>
                <p className="text-sm font-semibold text-slate-700 mb-3">Members ({ring.accountIds.length})</p>
                <div className="flex flex-wrap gap-2">
                  {ring.accountIds.map((accountId: string) => (
                    <span
                      key={accountId}
                      className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium ${
                        accountId.includes('FRAUD')
                          ? 'bg-red-100 text-red-800 border border-red-200'
                          : 'bg-orange-100 text-orange-800 border border-orange-200'
                      }`}
                    >
                      {accountId.includes('FRAUD') && <AlertCircle size={14} className="mr-1.5" />}
                      {maskAccountNumber(accountId)}
                    </span>
                  ))}
                </div>
              </div>

              {/* Detection Reason */}
              <div className="mt-4 pt-4 border-t border-slate-200">
                <p className="text-sm text-slate-600">
                  <span className="font-semibold">Detection Reason:</span> {ring.detectionReason}
                </p>
              </div>
            </div>
          ))}
          </div>

          {/* Load More Button */}
          <div className="mt-6 space-y-4" ref={sentinelRef}>
            {hasNextPage && !isLoadingMore && (
              <button
                onClick={loadMore}
                className="w-full px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Load More Fraud Rings
              </button>
            )}
            {isLoadingMore && (
              <div className="flex items-center justify-center py-4">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
                <span className="ml-3 text-slate-600">Loading more fraud rings...</span>
              </div>
            )}
            {!hasNextPage && rings.length > 0 && (
              <p className="text-sm text-slate-600 text-center py-2">
                ✓ All {rings.length} fraud ring(s) loaded
              </p>
            )}
          </div>
        </>
      )}

      {/* Information Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">📊 Understanding Fraud Rings</h3>
        <ul className="space-y-2 text-slate-700">
          <li>
            • A fraud ring is a group of accounts that share devices, phone numbers, or IP
            addresses
          </li>
          <li>• Shared identities suggest coordinated or identity-sharing activity</li>
          <li>• Accounts in the same ring are often controlled by the same person or group</li>
        </ul>
      </div>
    </div>
  )
}

export default FraudRings
