import { useEffect, useState } from 'react'
import { apiClient } from '../services/api'
import type { AccountDTO, AccountConnectionsDTO } from '../types/api'

export function useAccountDetails(accountId: string | null) {
  const [account, setAccount] = useState<AccountDTO | null>(null)
  const [connections, setConnections] = useState<AccountConnectionsDTO | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const refresh = async () => {
    if (!accountId) {
      setAccount(null)
      setConnections(null)
      return
    }

    try {
      setIsLoading(true)
      setError(null)
      const [accountData, connectionsData] = await Promise.all([
        apiClient.getAccountDetails(accountId),
        apiClient.getAccountConnections(accountId),
      ])
      setAccount(accountData)
      setConnections(connectionsData)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load account details'))
      setAccount(null)
      setConnections(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [accountId])

  return {
    account,
    connections,
    isLoading,
    error,
    refresh,
  }
}
