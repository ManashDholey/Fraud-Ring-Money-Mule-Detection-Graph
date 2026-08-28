import { useState, useCallback } from 'react'
import { GraphNodeDTO, GraphEdgeDTO } from '../types/api'
import { apiService } from '../services/api'

interface UseGraphLazyLoadOptions {
  initialDepth?: number
  onError?: (error: Error) => void
}

interface UseGraphLazyLoadState {
  nodes: GraphNodeDTO[]
  edges: GraphEdgeDTO[]
  loading: boolean
  loadingNodeId: string | null
  hasMoreConnections: boolean
  cursor: string | null
  error: Error | null
  loadGraph: (accountId: string, depth?: number) => Promise<void>
  expandNode: (nodeId: string, depth?: number) => Promise<void>
  reset: () => void
}

/**
 * Hook for lazy-loading graph data with cursor-based pagination.
 * Prevents loading entire graph at once, expands on demand.
 *
 * Usage:
 *   const { nodes, edges, loadGraph, expandNode } = useGraphLazyLoad()
 *   await loadGraph('ACC_123', 2)
 *   // render graph with nodes and edges
 *   await expandNode('nodeId', 3)
 *   // graph expands with new connections
 */
export function useGraphLazyLoad(
  options: UseGraphLazyLoadOptions = {}
): UseGraphLazyLoadState {
  const { initialDepth = 2, onError } = options

  const [nodes, setNodes] = useState<GraphNodeDTO[]>([])
  const [edges, setEdges] = useState<GraphEdgeDTO[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingNodeId, setLoadingNodeId] = useState<string | null>(null)
  const [hasMoreConnections, setHasMoreConnections] = useState(false)
  const [cursor, setCursor] = useState<string | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const loadGraph = useCallback(
    async (accountId: string, depth = initialDepth) => {
      try {
        setLoading(true)
        setError(null)
        setLoadingNodeId(null)

        const response = await apiService.getAccountGraph(accountId, depth)

        setNodes(response.nodes)
        setEdges(response.edges)
        setCursor(response.cursor || null)
        setHasMoreConnections(response.hasMoreConnections)
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to load graph')
        setError(error)
        onError?.(error)
      } finally {
        setLoading(false)
      }
    },
    [initialDepth, onError]
  )

  const expandNode = useCallback(
    async (nodeId: string, depth = initialDepth) => {
      if (loading || !cursor || !hasMoreConnections) return

      try {
        setLoading(true)
        setLoadingNodeId(nodeId)

        // Get current root account from nodes
        const rootNode = nodes.find(n => n.type === 'ACCOUNT')
        if (!rootNode) return

        const response = await apiService.expandAccountGraph(
          rootNode.id,
          cursor,
          depth
        )

        // Merge new nodes and edges, avoid duplicates
        setNodes(prev => {
          const existingIds = new Set(prev.map(n => n.id))
          const newNodes = response.nodes.filter(n => !existingIds.has(n.id))
          return [...prev, ...newNodes]
        })

        setEdges(prev => {
          const existingIds = new Set(prev.map(e => e.id))
          const newEdges = response.edges.filter(e => !existingIds.has(e.id))
          return [...prev, ...newEdges]
        })

        setCursor(response.cursor || null)
        setHasMoreConnections(response.hasMoreConnections)
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to expand graph')
        setError(error)
        onError?.(error)
      } finally {
        setLoading(false)
        setLoadingNodeId(null)
      }
    },
    [loading, cursor, hasMoreConnections, nodes, onError, initialDepth]
  )

  const reset = useCallback(() => {
    setNodes([])
    setEdges([])
    setCursor(null)
    setHasMoreConnections(false)
    setError(null)
    setLoadingNodeId(null)
  }, [])

  return {
    nodes,
    edges,
    loading,
    loadingNodeId,
    hasMoreConnections,
    cursor,
    error,
    loadGraph,
    expandNode,
    reset,
  }
}
