import React, { useState, useMemo } from 'react'
import { ArrowRight, Loader } from 'lucide-react'
import { formatCurrency, formatDateTime, maskAccountNumber } from '../utils/formatting'
import { useMoneyMuleTransactions } from '../hooks/useMoneyMuleTransactions'

const Transactions: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('')
  const { transactions, isLoading, error } = useMoneyMuleTransactions()

  // Filter transactions based on search query
  const filteredTransactions = useMemo(() => {
    if (!searchQuery.trim()) return transactions
    
    const query = searchQuery.toLowerCase()
    return transactions.filter(
      (txn) =>
        txn.id.toLowerCase().includes(query) ||
        txn.from.toLowerCase().includes(query) ||
        txn.to.toLowerCase().includes(query)
    )
  }, [transactions, searchQuery])

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Transaction Explorer</h1>
        <p className="text-slate-600">
          View and analyze transactions related to fraud investigations
        </p>
      </div>

      {/* Search Bar */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <input
          type="text"
          placeholder="Search by transaction ID or account..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Transactions List */}
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : error ? (
          <div className="p-6 text-center">
            <p className="text-red-600">Error loading transactions: {error.message}</p>
          </div>
        ) : filteredTransactions.length === 0 ? (
          <div className="p-6 text-center">
            <p className="text-slate-600">
              {searchQuery ? 'No transactions match your search' : 'No transactions found'}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                      Transaction ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                      From
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider" />
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                      To
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                      Amount
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                      Time
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 uppercase tracking-wider">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {filteredTransactions.map((transaction) => (
                    <tr key={transaction.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 text-sm font-mono text-slate-600">
                        {transaction.id}
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-slate-900">
                        {maskAccountNumber(transaction.from)}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <ArrowRight size={18} className="text-slate-400" />
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-slate-900">
                        {maskAccountNumber(transaction.to)}
                      </td>
                      <td className="px-6 py-4 text-sm font-bold text-slate-900">
                        {formatCurrency(transaction.amount)}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">
                        {formatDateTime(transaction.timestamp)}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          {transaction.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-slate-50 px-6 py-4 border-t border-slate-200">
              <p className="text-sm text-slate-600">
                Showing <span className="font-semibold">{filteredTransactions.length}</span> of{' '}
                <span className="font-semibold">{transactions.length}</span> transaction(s)
              </p>
            </div>
          </>
        )}
      </div>

      {/* Information Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">💡 Money-Mule Detection</h3>
        <p className="text-slate-700 mb-4">
          Money-mule chains show how funds flow through multiple accounts to obscure the source.
          The sequence above shows a typical pattern:
        </p>
        <ul className="space-y-2 text-slate-700">
          <li>
            • <strong>Fraud Account</strong> sends large amount to intermediary
          </li>
          <li>
            • <strong>Intermediaries</strong> (mules) quickly forward funds to next account
          </li>
          <li>
            • <strong>Final Recipient</strong> may be legitimate account unaware of fraud
          </li>
          <li>
            • Losses mount as each intermediary takes a commission
          </li>
        </ul>
      </div>
    </div>
  )
}

export default Transactions
