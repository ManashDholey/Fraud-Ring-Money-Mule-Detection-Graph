import { useReducer, useCallback } from 'react'
import type { GraphNodeDTO, GraphEdgeDTO } from '../types/api'

/**
 * Graph state management hook.
 * Owns the merged graph state and handles incremental node expansion with dedup.
 * Phase 6: Proper incremental graph loading with per-node tracking.
 */

interface GraphState {
  nodes: GraphNodeDTO[]
  edges: GraphEdgeDTO[]
  expandingNodeIds: Set<string>
}

type GraphAction =
  | { type: 'RESET_GRAPH'; nodes: GraphNodeDTO[]; edges: GraphEdgeDTO[] }
  | { type: 'MERGE_EXPANSION'; nodeId: string; nodes: GraphNodeDTO[]; edges: GraphEdgeDTO[] }
  | { type: 'SET_EXPANDING'; nodeId: string }
  | { type: 'CLEAR_EXPANDING'; nodeId: string }

function graphReducer(state: GraphState, action: GraphAction): GraphState {
  switch (action.type) {
    case 'RESET_GRAPH': {
      return {
        nodes: action.nodes,
        edges: action.edges,
        expandingNodeIds: new Set<string>(),
      }
    }

    case 'MERGE_EXPANSION': {
      const nodeIdMap = new Map(state.nodes.map(n => [n.id, n]))
      const edgeIdMap = new Map(state.edges.map(e => [e.id, e]))

      // Merge nodes with dedup by id
      for (const newNode of action.nodes) {
        if (!nodeIdMap.has(newNode.id)) {
          nodeIdMap.set(newNode.id, newNode)
        }
      }

      // Merge edges with dedup by id
      for (const newEdge of action.edges) {
        if (!edgeIdMap.has(newEdge.id)) {
          edgeIdMap.set(newEdge.id, newEdge)
        }
      }

      return {
        nodes: Array.from(nodeIdMap.values()),
        edges: Array.from(edgeIdMap.values()),
        expandingNodeIds: state.expandingNodeIds,
      }
    }

    case 'SET_EXPANDING': {
      const newSet = new Set(state.expandingNodeIds)
      newSet.add(action.nodeId)
      return { ...state, expandingNodeIds: newSet }
    }

    case 'CLEAR_EXPANDING': {
      const newSet = new Set(state.expandingNodeIds)
      newSet.delete(action.nodeId)
      return { ...state, expandingNodeIds: newSet }
    }

    default:
      return state
  }
}

export interface UseGraphStateResult {
  nodes: GraphNodeDTO[]
  edges: GraphEdgeDTO[]
  isExpandingNode: (nodeId: string) => boolean
  resetGraph: (nodes: GraphNodeDTO[], edges: GraphEdgeDTO[]) => void
  mergeExpansion: (nodeId: string, nodes: GraphNodeDTO[], edges: GraphEdgeDTO[]) => void
  setExpanding: (nodeId: string) => void
  clearExpanding: (nodeId: string) => void
}

export function useGraphState(): UseGraphStateResult {
  const [state, dispatch] = useReducer(graphReducer, {
    nodes: [],
    edges: [],
    expandingNodeIds: new Set<string>(),
  } as GraphState)

  const resetGraph = useCallback((nodes: GraphNodeDTO[], edges: GraphEdgeDTO[]) => {
    dispatch({ type: 'RESET_GRAPH', nodes, edges } as GraphAction)
  }, [])

  const mergeExpansion = useCallback(
    (nodeId: string, nodes: GraphNodeDTO[], edges: GraphEdgeDTO[]) => {
      dispatch({ type: 'MERGE_EXPANSION', nodeId, nodes, edges } as GraphAction)
    },
    []
  )

  const setExpanding = useCallback((nodeId: string) => {
    dispatch({ type: 'SET_EXPANDING', nodeId } as GraphAction)
  }, [])

  const clearExpanding = useCallback((nodeId: string) => {
    dispatch({ type: 'CLEAR_EXPANDING', nodeId } as GraphAction)
  }, [])

  const isExpandingNode = useCallback(
    (nodeId: string) => state.expandingNodeIds.has(nodeId),
    [state.expandingNodeIds]
  )

  return {
    nodes: state.nodes,
    edges: state.edges,
    isExpandingNode,
    resetGraph,
    mergeExpansion,
    setExpanding,
    clearExpanding,
  }
}
