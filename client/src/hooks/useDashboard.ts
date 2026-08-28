import { useEffect, useState } from 'react'
import { apiClient } from '../services/api'
import { DashboardStatsDTO } from '../types/api'

export function useDashboard() {
  const [stats, setStats] = useState<DashboardStatsDTO | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const refresh = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await apiClient.getDashboard()

      setStats(response)
    } catch (err) {
      const nextError = err instanceof Error ? err : new Error('Failed to load dashboard metrics')
      setError(nextError)
      setStats(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  return {
    stats,
    isLoading,
    error,
    refresh,
  }
}
