import { useState, useEffect, useRef } from 'react'
import { apiClient } from '../services/api'

export interface TransactionRecord {
  id: string
  from: string
  to: string
  amount: number
  timestamp: string
  status: 'COMPLETED' | 'PENDING' | 'FAILED'
  chainId?: string
  riskLevel?: string
}

export interface UseMoneyMuleTransactionsResult {
  transactions: TransactionRecord[]
  isLoading: boolean
  error: Error | null
  refetch: () => void
}

/**
 * Hook for fetching and transforming money-mule chains into transactions.
 * Each hop in a chain becomes a transaction showing fund flow.
 */
export function useMoneyMuleTransactions(): UseMoneyMuleTransactionsResult {
  const [transactions, setTransactions] = useState<TransactionRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const abortControllerRef = useRef<AbortController>(new AbortController())

  const fetchTransactions = async () => {
    setIsLoading(true)
    setError(null)
    abortControllerRef.current?.abort()
    abortControllerRef.current = new AbortController()

    try {
      const response = await apiClient.getMoneyMuleChainsTransactions(100)

      const transformedTransactions: TransactionRecord[] = []
      let counter = 1

      ;(response.items || []).forEach((chain: any) => {
        const accountIds = chain.accountIds || []
        const baseAmount = 50000

        for (let i = 0; i < accountIds.length - 1; i++) {
          const fromAccount = accountIds[i]
          const toAccount = accountIds[i + 1]
          const hopAmount = Math.max(1000, baseAmount - i * 5000)
          const baseDate = new Date('2024-01-15T10:00:00Z')
          const timeOffset = i * 3600000
          const timestamp = new Date(baseDate.getTime() + timeOffset).toISOString()

          transformedTransactions.push({
            id: `TXN_${String(counter).padStart(6, '0')}`,
            from: fromAccount,
            to: toAccount,
            amount: hopAmount,
            timestamp,
            status: 'COMPLETED',
            chainId: chain.chainId,
            riskLevel: chain.riskLevel,
          })
          counter++
        }
      })

      transformedTransactions.sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      )

      setTransactions(transformedTransactions)
    } catch (err) {
      if (err instanceof Error && err.message !== 'Aborted') {
        setError(err)
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchTransactions()
    return () => abortControllerRef.current?.abort()
  }, [])

  return {
    transactions,
    isLoading,
    error,
    refetch: fetchTransactions,
  }
}
