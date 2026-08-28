import { useEffect, useCallback, useMemo, useReducer } from 'react'

/**
 * Generic paginated resource hook - eliminates duplicated pagination logic.
 * Phase 4: Shared helper for useAccounts, useTransactions, useFraudRings.
 */

export interface PaginatedHookResult<T> {
  items: T[]
  hasNextPage: boolean
  isLoading: boolean
  isLoadingMore: boolean
  error: Error | null
  loadMore: () => Promise<void>
  reset: () => Promise<void>
}

interface PaginatedState<T> {
  items: T[]
  hasNextPage: boolean
  isLoading: boolean
  isLoadingMore: boolean
  error: Error | null
  nextCursor: string | null
}

type PaginatedAction<T> =
  | { type: 'SET_LOADING' }
  | { type: 'SET_LOADED'; payload: { items: T[]; cursor: string | null; hasNextPage: boolean } }
  | { type: 'SET_ERROR'; payload: Error }
  | { type: 'SET_LOADING_MORE' }
  | { type: 'APPEND_ITEMS'; payload: { items: T[]; cursor: string | null; hasNextPage: boolean } }
  | { type: 'SET_LOADING_MORE_DONE' }
  | { type: 'RESET_ERROR' }

function paginatedReducer<T>(state: PaginatedState<T>, action: PaginatedAction<T>): PaginatedState<T> {
  if (import.meta.env.DEV) {
    console.log('[paginatedReducer] Action:', action.type, 'Old state items:', state.items.length)
  }
  
  switch (action.type) {
    case 'SET_LOADING':
      const loadingState = { ...state, isLoading: true, error: null }
      if (import.meta.env.DEV) {
        console.log('[paginatedReducer] SET_LOADING - new state isLoading:', loadingState.isLoading)
      }
      return loadingState
    case 'SET_LOADED':
      const loadedState = {
        ...state,
        items: action.payload.items,
        nextCursor: action.payload.cursor,
        hasNextPage: action.payload.hasNextPage,
        isLoading: false,
        error: null,
      }
      if (import.meta.env.DEV) {
        console.log('[paginatedReducer] SET_LOADED - new state items:', loadedState.items.length, 'isLoading:', loadedState.isLoading)
      }
      return loadedState
    case 'SET_ERROR':
      return { ...state, error: action.payload, items: [], isLoading: false }
    case 'SET_LOADING_MORE':
      return { ...state, isLoadingMore: true, error: null }
    case 'APPEND_ITEMS':
      return {
        ...state,
        items: [...state.items, ...action.payload.items],
        nextCursor: action.payload.cursor,
        hasNextPage: action.payload.hasNextPage,
        isLoadingMore: false,
      }
    case 'SET_LOADING_MORE_DONE':
      return { ...state, isLoadingMore: false }
    case 'RESET_ERROR':
      return { ...state, error: null }
    default:
      return state
  }
}

export interface PaginatedResourceOptions<TFilters> {
  fetchPage: (cursor: string | null, filters: TFilters) => Promise<{
    items: unknown[]
    cursor: string | null
    hasNextPage: boolean
  }>
  filters: TFilters
  getItemId: (item: unknown) => string
  initialLoad?: boolean
}

export function usePaginatedResource<T, TFilters>(
  fetchPage: (cursor: string | null, filters: TFilters) => Promise<{
    items: T[]
    cursor: string | null
    hasNextPage: boolean
  }>,
  filters: TFilters,
  getItemId: (item: T) => string
): PaginatedHookResult<T> {
  console.log('[usePaginatedResource] Hook called with filters:', filters)
  
  const initialState: PaginatedState<T> = {
    items: [],
    hasNextPage: false,
    isLoading: true,  // Start as true to show loading initially
    isLoadingMore: false,
    error: null,
    nextCursor: null,
  }

  const [state, dispatch] = useReducer(paginatedReducer<T>, initialState)

  // Serialize filters to create a stable dependency - use ONLY this, not the object itself
  const filterKey = useMemo(() => JSON.stringify(filters), [filters])

  // Reset when filters change - fetch logic directly in effect
  useEffect(() => {
    // Each effect invocation gets its own independent ignore flag via closure
    // This correctly handles StrictMode's mount->cleanup->mount pattern
    let ignore = false

    const performFetch = async () => {
      try {
        console.log('[usePaginatedResource] Effect: Starting fetch with filterKey:', filterKey)
        dispatch({ type: 'SET_LOADING' })

        const response = await fetchPage(null, filters)
        console.log('[usePaginatedResource] Effect: Fetch completed, got', response.items?.length || 0, 'items')

        // Check the local ignore flag (set by THIS effect's cleanup only)
        if (ignore) {
          console.log('[usePaginatedResource] Effect: Effect was replaced/cleaned up, discarding response')
          return
        }

        console.log('[usePaginatedResource] Effect: Dispatching SET_LOADED')
        dispatch({
          type: 'SET_LOADED',
          payload: {
            items: response.items,
            cursor: response.cursor ?? null,
            hasNextPage: response.hasNextPage,
          },
        })
        console.log('[usePaginatedResource] Effect: SET_LOADED dispatched, state should update')
      } catch (err) {
        console.error('[usePaginatedResource] Effect: Fetch error:', err)
        if (ignore) {
          console.log('[usePaginatedResource] Effect: Effect was replaced/cleaned up after error, discarding')
          return
        }
        dispatch({
          type: 'SET_ERROR',
          payload: err instanceof Error ? err : new Error('Failed to load items'),
        })
      }
    }

    console.log('[usePaginatedResource] >>>>>> EFFECT RUNNING, filterKey:', filterKey)
    void performFetch()

    // Cleanup for THIS effect invocation - sets THIS invocation's ignore flag
    return () => {
      ignore = true
    }
  }, [filterKey])  // Only depend on memoized filterKey, NOT raw filters object

  const reset = useCallback(async () => {
    // This is now a no-op, kept for API compatibility
    // Actual reset happens in useEffect above
  }, [])

  const loadMore = useCallback(async () => {
    if (state.isLoadingMore || !state.hasNextPage || !state.nextCursor) return

    try {
      dispatch({ type: 'SET_LOADING_MORE' })

      const response = await fetchPage(state.nextCursor, filters)

      // Dedup by id before merging
      const seen = new Set(state.items.map(item => getItemId(item)))
      const newItems = response.items.filter(item => {
        const id = getItemId(item)
        if (seen.has(id)) return false
        seen.add(id)
        return true
      })

      dispatch({
        type: 'APPEND_ITEMS',
        payload: {
          items: newItems,
          cursor: response.cursor ?? null,
          hasNextPage: response.hasNextPage,
        },
      })
    } catch (err) {
      dispatch({
        type: 'SET_ERROR',
        payload: err instanceof Error ? err : new Error('Failed to load more'),
      })
    }
  }, [state.isLoadingMore, state.hasNextPage, state.nextCursor, state.items, fetchPage, filters, getItemId])

  return {
    items: state.items,
    hasNextPage: state.hasNextPage,
    isLoading: state.isLoading,
    isLoadingMore: state.isLoadingMore,
    error: state.error,
    loadMore,
    reset,
  }
}
