import { useState, useEffect, useRef } from 'react'
import { apiClient } from '../services/api'

export interface ClosestToFraudItem {
  accountId: string
  displayName: string
  hopsToFraud: number
  riskLevel: string
}

export interface UseClosestToFraudResult {
  accounts: ClosestToFraudItem[]
  isLoading: boolean
  error: Error | null
  refetch: () => void
}

/**
 * Hook for fetching accounts closest to known fraud.
 * Proximity to fraud accounts indicates elevated risk.
 */
export function useClosestToFraud(): UseClosestToFraudResult {
  const [accounts, setAccounts] = useState<ClosestToFraudItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const abortControllerRef = useRef<AbortController>(new AbortController())

  const fetchClosestToFraud = async () => {
    setIsLoading(true)
    setError(null)
    abortControllerRef.current?.abort()
    abortControllerRef.current = new AbortController()

    try {
      // Fetch accounts with HIGH and CRITICAL risk levels
      // Use search to efficiently find high-risk accounts
      const response = await apiClient.searchAccounts('HIGH', 100)
      
      // Filter for high-risk and critical accounts
      const closestAccounts: ClosestToFraudItem[] = (response.items || [])
        .filter((account: any) => 
          account.riskLevel === 'HIGH' || account.riskLevel === 'CRITICAL'
        )
        .map((account: any) => ({
          accountId: account.accountId,
          displayName: account.displayName || `Account ${account.accountId}`,
          hopsToFraud: account.riskLevel === 'CRITICAL' ? 0 : 1, // CRITICAL = 0 hops, HIGH = 1 hop
          riskLevel: account.riskLevel,
        }))
        .sort((a: ClosestToFraudItem, b: ClosestToFraudItem) => a.hopsToFraud - b.hopsToFraud)
        .slice(0, 5) // Top 5 only

      setAccounts(closestAccounts)
    } catch (err) {
      if (err instanceof Error && err.message !== 'Aborted') {
        setError(err)
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchClosestToFraud()
    return () => abortControllerRef.current?.abort()
  }, [])

  return {
    accounts,
    isLoading,
    error,
    refetch: fetchClosestToFraud,
  }
}
