import { useCallback, useMemo } from 'react'
import type { AccountDTO } from '../types/api'
import { apiClient } from '../services/api'
import { usePaginatedResource, type PaginatedHookResult } from './internal/usePaginatedResource'

export interface AccountFilters {
  query?: string
  riskLevel?: string
  knownFraud?: boolean
}

/**
 * Hook for fetching paginated account list with search/filter.
 * Uses shared usePaginatedResource helper to eliminate duplicated pagination logic.
 * Resets and refetches on filter change.
 */
export function useAccountPagination(filters: AccountFilters = {}): PaginatedHookResult<AccountDTO> {
  const fetchPage = useCallback(
    async (cursor: string | null, currentFilters: AccountFilters) => {
      const response = await apiClient.searchAccounts(currentFilters.query, 25, cursor ?? undefined)
      console.log('Fetched accounts:', response.items) // Debugging line to check the fetched items
      return {
        items: response.items,
        cursor: response.cursor ?? null,
        hasNextPage: response.hasNextPage,
      }
    },
    []
  )

  const getItemId = useCallback((account: AccountDTO) => account.accountId, [])

  // Memoize filters to prevent unnecessary re-fetches
  const memoizedFilters = useMemo(() => filters, [filters.query, filters.riskLevel, filters.knownFraud])

  return usePaginatedResource(fetchPage, memoizedFilters, getItemId)
}
