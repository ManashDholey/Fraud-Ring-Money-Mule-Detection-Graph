import { useCallback, useMemo } from 'react'
import type { FraudRingDTO } from '../types/api'
import { apiClient } from '../services/api'
import { usePaginatedResource, type PaginatedHookResult } from './internal/usePaginatedResource'

/**
 * Hook for fetching paginated fraud rings list.
 * Uses shared usePaginatedResource helper to eliminate duplicated pagination logic.
 * @param pageSize - Number of items to fetch per page (default: 25, max: 100)
 */
export function useFraudRings(pageSize: number = 25): PaginatedHookResult<FraudRingDTO> {
  const clampedPageSize = Math.max(1, Math.min(100, pageSize))
  
  const fetchPage = useCallback(async (cursor: string | null) => {
    const response = await apiClient.getFraudRings(clampedPageSize, cursor ?? undefined)
    return {
      items: response.items,
      cursor: response.cursor ?? null,
      hasNextPage: response.hasNextPage,
    }
  }, [clampedPageSize])

  const getItemId = useCallback((ring: FraudRingDTO) => ring.ringId, [])
  
  // Memoize the filters object so it doesn't change on every render
  // This prevents the effect in usePaginatedResource from re-triggering unnecessarily
  const filters = useMemo(() => ({}), [])

  return usePaginatedResource(fetchPage, filters, getItemId)
}
