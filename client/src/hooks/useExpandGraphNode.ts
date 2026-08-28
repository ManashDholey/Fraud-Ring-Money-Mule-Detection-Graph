import { useState, useRef, useCallback } from 'react'
import { apiClient } from '../services/api'
import type { GraphNodeDTO, GraphEdgeDTO } from '../types/api'

/**
 * Hook for expanding a graph node to load its additional connections.
 * Responsibility: Fetch NEW nodes/edges from a specific node using cursor-based pagination.
 * Does NOT own or manage the merged graph state — caller merges results.
 */
export function useExpandGraphNode() {
  const [loadingNodeId, setLoadingNodeId] = useState<string | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const expandNode = useCallback(
    async (
      nodeId: string,
      accountId: string,
      cursor?: string
    ): Promise<{ nodes: GraphNodeDTO[]; edges: GraphEdgeDTO[] }> => {
      abortControllerRef.current?.abort()
      abortControllerRef.current = new AbortController()

      try {
        setLoadingNodeId(nodeId)
        setError(null)

        const response = await apiClient.expandAccountGraph(accountId, cursor ?? '', 2)

        if (abortControllerRef.current.signal.aborted) {
          return { nodes: [], edges: [] }
        }

        return {
          nodes: response.nodes ?? [],
          edges: response.edges ?? [],
        }
      } catch (err) {
        if (abortControllerRef.current.signal.aborted) {
          return { nodes: [], edges: [] }
        }

        const nextError = err instanceof Error ? err : new Error('Failed to expand graph node')
        setError(nextError)
        return { nodes: [], edges: [] }
      } finally {
        setLoadingNodeId(null)
      }
    },
    []
  )

  return {
    expandNode,
    loadingNodeId,
    error,
  }
}
