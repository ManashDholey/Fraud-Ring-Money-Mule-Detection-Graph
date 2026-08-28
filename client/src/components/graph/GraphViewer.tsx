import React, { useEffect, useState, useCallback, useRef } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MiniMap,
  Connection,
  addEdge,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Loader } from 'lucide-react'
import { ErrorState, LoadingSkeleton } from '../common'
import { useAccountGraph } from '../../hooks/useAccountGraph'
import { useExpandGraphNode } from '../../hooks/useExpandGraphNode'
import { useInvestigation } from '../../contexts/InvestigationContext'
import type { GraphResponseDTO, GraphNodeDTO, GraphEdgeDTO } from '../../types/api'

interface GraphViewerProps {
  accountId: string
}

// Determine node color based on risk level or node type
const getNodeColor = (node: GraphNodeDTO, nodeType: string): string => {
  const riskLevel = node.riskLevel

  if (nodeType === 'ACCOUNT') {
    switch (riskLevel) {
      case 'CRITICAL':
        return '#dc2626'
      case 'HIGH':
        return '#ea580c'
      case 'MEDIUM':
        return '#eab308'
      case 'LOW':
        return '#16a34a'
      default:
        return '#1e40af'
    }
  }

  // Non-account nodes get neutral colors
  switch (nodeType) {
    case 'CARD':
      return '#3b82f6'
    case 'DEVICE':
      return '#64748b'
    case 'PHONE_NUMBER':
      return '#7c3aed'
    case 'IP_ADDRESS':
      return '#0891b2'
    case 'TRANSACTION':
      return '#059669'
    default:
      return '#6b7280'
  }
}

// Extract a readable label from node data
const getNodeLabel = (node: GraphNodeDTO, nodeType: string): string => {
  if (nodeType === 'ACCOUNT') {
    return node.label || (node.id ? node.id.substring(0, 8) : 'Account')
  }

  if (nodeType === 'CARD' && node.metadata) {
    const cardNumber = node.metadata['cardNumber']
    if (typeof cardNumber === 'string') {
      const lastFour = cardNumber.slice(-4)
      return lastFour ? `••${lastFour}` : 'Card'
    }
    return 'Card'
  }

  if (nodeType === 'DEVICE' && node.metadata) {
    const deviceName = node.metadata['deviceName']
    if (typeof deviceName === 'string') return deviceName
    return node.label || 'Device'
  }

  if (nodeType === 'PHONE_NUMBER') {
    return 'Phone'
  }

  if (nodeType === 'IP_ADDRESS' && node.metadata) {
    const ipAddress = node.metadata['ipAddress']
    if (typeof ipAddress === 'string') return ipAddress
    return node.label || 'IP'
  }

  if (nodeType === 'TRANSACTION' && node.metadata) {
    const amount = node.metadata['amount']
    if (typeof amount === 'number') return `$${amount}`
    return 'Txn'
  }

  return node.label || nodeType
}

// Helper to create a React Flow node from graph node data
const createReactFlowNode = (
  nodeData: GraphNodeDTO,
  isLoadingNode?: boolean,
  hasExpansionError?: boolean
): Node => {
  const nodeId = nodeData.id
  const nodeType = nodeData.type || 'ACCOUNT'
  const color = getNodeColor(nodeData, nodeType)
  const displayLabel = getNodeLabel(nodeData, nodeType)

  return {
    id: nodeId,
    data: { 
      label: displayLabel,
      isLoading: isLoadingNode,
      hasError: hasExpansionError,
    },
    position: { x: 0, y: 0 },
    style: {
      background: color,
      border: nodeType === 'ACCOUNT' ? '3px solid #1e40af' : '2px solid rgba(0,0,0,0.1)',
      borderRadius: '8px',
      color: 'white',
      fontWeight: nodeType === 'ACCOUNT' ? 'bold' : '600',
      fontSize: nodeType === 'ACCOUNT' ? '13px' : '11px',
      width: nodeType === 'ACCOUNT' ? 120 : 100,
      height: nodeType === 'ACCOUNT' ? 80 : 60,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center',
      padding: '8px',
      boxShadow: isLoadingNode ? '0 0 12px rgba(59, 130, 246, 0.8)' : 
                 hasExpansionError ? '0 0 12px rgba(220, 38, 38, 0.8)' :
                 '0 2px 8px rgba(0,0,0,0.15)',
      whiteSpace: 'pre-wrap' as const,
      wordBreak: 'break-word' as const,
      cursor: nodeType !== 'ACCOUNT' ? 'pointer' : 'default',
      opacity: isLoadingNode ? 0.8 : 1,
    },
  }
}

const GraphViewer: React.FC<GraphViewerProps> = ({ accountId }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [graphError, setGraphError] = useState<string | null>(null)
  const [nodeExpansionErrors, setNodeExpansionErrors] = useState<Map<string, string>>(new Map())
  
  const investigation = useInvestigation()
  const { nodes: graphNodes, edges: graphEdges, isLoading, error } = useAccountGraph(accountId, investigation.state.graphDepth)
  const { expandNode, loadingNodeId } = useExpandGraphNode()
  const nodeMapRef = useRef<Map<string, GraphNodeDTO>>(new Map())

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges]
  )

  // Handle node expansion on click
  const handleNodeClick = useCallback(
    async (nodeId: string) => {
      investigation.selectNode(nodeId)
      
      // Only expand if not already loading and within depth limit
      if (loadingNodeId === nodeId || investigation.state.graphDepth >= 4 || !accountId) {
        return
      }

      try {
        const result = await expandNode(nodeId, accountId)
        
        // Merge new nodes and edges, deduplicating by ID
        setNodes((prevNodes) => {
          const nodeMap = new Map(prevNodes.map((n) => [n.id, n]))
          const nodeDataMap = new Map(nodeMapRef.current)
          
          result.nodes.forEach((newNode) => {
            if (!nodeMap.has(newNode.id)) {
              nodeDataMap.set(newNode.id, newNode)
              const reactFlowNode = createReactFlowNode(newNode)
              nodeMap.set(newNode.id, reactFlowNode)
            }
          })
          
          nodeMapRef.current = nodeDataMap
          return Array.from(nodeMap.values())
        })

        setEdges((prevEdges) => {
          const edgeSet = new Set(prevEdges.map((e) => e.id))
          const newEdges = [...prevEdges]
          
          result.edges.forEach((newEdge) => {
            const edgeId = `${newEdge.source}-${newEdge.target}-${newEdge.relationship}`
            if (!edgeSet.has(edgeId)) {
              newEdges.push({
                id: edgeId,
                source: newEdge.source,
                target: newEdge.target,
                animated: true,
                label: newEdge.relationship,
              })
            }
          })
          
          return newEdges
        })

        investigation.toggleExpandedNode(nodeId)
        setNodeExpansionErrors((prev) => {
          const next = new Map(prev)
          next.delete(nodeId)
          return next
        })
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to expand node'
        setNodeExpansionErrors((prev) => new Map(prev).set(nodeId, errorMsg))
      }
    },
    [accountId, expandNode, investigation, loadingNodeId]
  )

  useEffect(() => {
    if (!graphNodes.length && !graphEdges.length && !isLoading) {
      setGraphError(error ? 'Failed to load graph visualization.' : null)
      return
    }

    setGraphError(null)
    buildGraph({ nodes: graphNodes, edges: graphEdges, hasMoreConnections: false })
  }, [graphNodes, graphEdges, isLoading, error])

  const buildGraph = (graphData: GraphResponseDTO) => {
    const nodeMap = new Map<string, Node>()
    const nodeDataMap = new Map<string, GraphNodeDTO>()
    const edgeList: Edge[] = []

    // Group nodes by type for layout
    const nodesByType = new Map<string, GraphNodeDTO[]>()

    // Process nodes
    if (graphData.nodes && graphData.nodes.length > 0) {
      graphData.nodes.forEach((nodeData) => {
        const nodeId = nodeData.id
        const nodeType = nodeData.type || 'ACCOUNT'

        // Deduplicate: skip if already exists
        if (nodeMap.has(nodeId)) {
          return
        }

        // Group by type
        if (!nodesByType.has(nodeType)) {
          nodesByType.set(nodeType, [])
        }
        nodesByType.get(nodeType)!.push(nodeData)
        nodeDataMap.set(nodeId, nodeData)

        const isLoading = loadingNodeId === nodeId
        const hasError = nodeExpansionErrors.has(nodeId)
        const reactFlowNode = createReactFlowNode(nodeData, isLoading, hasError)
        nodeMap.set(nodeId, reactFlowNode)
      })
    }

    // Apply layout: arrange nodes by type in columns
    let yOffset = 0
    const colWidth = 200
    let colIndex = 0

    nodesByType.forEach((nodesOfType) => {
      nodesOfType.forEach((node, idx) => {
        const reactFlowNode = nodeMap.get(node.id)
        if (reactFlowNode) {
          reactFlowNode.position = {
            x: colIndex * colWidth,
            y: yOffset + idx * 150,
          }
        }
      })
      colIndex++
      yOffset += 100
    })

    // Process relationships/edges
    if (graphData.edges && graphData.edges.length > 0) {
      graphData.edges.forEach((edgeData: GraphEdgeDTO) => {
        const sourceId = edgeData.source
        const targetId = edgeData.target

        if (nodeMap.has(sourceId) && nodeMap.has(targetId)) {
          const edgeId = `${sourceId}-${targetId}-${edgeData.relationship}`
          if (!edgeList.some((e) => e.id === edgeId)) {
            edgeList.push({
              id: edgeId,
              source: sourceId,
              target: targetId,
              animated: true,
              label: edgeData.relationship,
            })
          }
        }
      })
    }

    nodeMapRef.current = nodeDataMap
    setNodes(Array.from(nodeMap.values()))
    setEdges(edgeList)
  }

  if (isLoading) {
    return <LoadingSkeleton rows={3} columns={3} />
  }

  if (error || graphError) {
    return (
      <ErrorState
        title="Graph Visualization Error"
        message={error?.message ?? graphError ?? 'Failed to load graph visualization.'}
        onRetry={() => window.location.reload()}
      />
    )
  }

  if (nodes.length === 0) {
    return (
      <div className="w-full h-96 flex items-center justify-center bg-slate-50 rounded-lg border-2 border-dashed border-slate-300">
        <p className="text-slate-600">No graph data available for this account.</p>
      </div>
    )
  }

  return (
    <div style={{ width: '100%', height: '600px' }} className="rounded-lg overflow-hidden border border-slate-200">
      <ReactFlow
        nodes={nodes.map((node) => ({
          ...node,
          style: {
            ...node.style,
            cursor: investigation.state.expandedNodeIds.has(node.id) ? 'default' : 'pointer',
          },
        }))}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={(_, node) => handleNodeClick(node.id)}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>

      {/* Per-node loading and error indicators */}
      {loadingNodeId && (
        <div className="absolute bottom-4 right-4 flex items-center gap-2 bg-white px-4 py-2 rounded-lg shadow-md border border-blue-200">
          <Loader className="h-4 w-4 animate-spin text-blue-600" />
          <span className="text-sm text-slate-600">Expanding node...</span>
        </div>
      )}

      {nodeExpansionErrors.size > 0 && (
        <div className="absolute bottom-4 right-4 bg-red-50 border border-red-200 px-4 py-3 rounded-lg shadow-md">
          <p className="text-sm font-medium text-red-900">Expansion Errors:</p>
          {Array.from(nodeExpansionErrors.entries()).map(([nodeId, error]) => (
            <p key={nodeId} className="text-xs text-red-700 mt-1">
              {error}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

export default GraphViewer
