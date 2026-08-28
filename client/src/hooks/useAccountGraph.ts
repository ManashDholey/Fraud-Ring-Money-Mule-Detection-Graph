import { useEffect, useState, useRef, useCallback } from 'react'
import { apiClient } from '../services/api'
import type { GraphNodeDTO, GraphEdgeDTO } from '../types/api'

/**
 * Hook for loading the INITIAL bounded neighborhood of an account.
 * Responsibility: Fetch and return only the initial graph (depth-limited).
 * Does NOT handle expansion — that's useExpandGraphNode's job.
 */
export function useAccountGraph(accountId: string | null, depth = 1) {
  const [nodes, setNodes] = useState<GraphNodeDTO[]>([])
  const [edges, setEdges] = useState<GraphEdgeDTO[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const refetch = useCallback(async () => {
    if (!accountId) {
      setNodes([])
      setEdges([])
      return
    }

    // Abort any in-flight request
    abortControllerRef.current?.abort()
    abortControllerRef.current = new AbortController()
    
    // Capture the current abort controller for this request
    const currentAbortController = abortControllerRef.current

    try {
      setIsLoading(true)
      setError(null)

      const graphData = await apiClient.getAccountGraph(accountId, Math.min(depth, 3))

      // Check if this request was aborted or superseded
      if (currentAbortController.signal.aborted) return

      setNodes(graphData.nodes)
      setEdges(graphData.edges)
    } catch (err) {
      // Check if this request was aborted (not an actual error)
      if (currentAbortController.signal.aborted) return

      setError(err instanceof Error ? err : new Error('Failed to load graph'))
      setNodes([])
      setEdges([])
    } finally {
      // Only set loading to false if this is still the current request
      if (!currentAbortController.signal.aborted) {
        setIsLoading(false)
      }
    }
  }, [accountId, depth])

  useEffect(() => {
    void refetch()
    
    // Cleanup: abort any pending request when effect unmounts
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [refetch])

  return {
    nodes,
    edges,
    isLoading,
    error,
    refetch,
  }
}
