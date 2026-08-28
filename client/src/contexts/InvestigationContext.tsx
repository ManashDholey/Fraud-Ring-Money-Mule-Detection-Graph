import { useContext, useCallback } from 'react'
import type { ReactNode } from 'react'
import React, { createContext, useReducer, useMemo } from 'react'

// Investigation Context API - Phase 2 Refactor
// Stores ONLY UI/investigation state — NOT server data
// All state transitions use useReducer for atomic, testable mutations

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | null
export type RelationshipType = 'HAS_CARD' | 'USES_DEVICE' | 'HAS_PHONE' | 'ACCESSED_FROM_IP' | 'TRANSACTED_WITH'

interface InvestigationState {
  selectedAccountId: string | null
  selectedNodeId: string | null
  graphDepth: number
  expandedNodeIds: Set<string>
  relationshipFilters: Set<RelationshipType>
  riskFilter: RiskLevel
  accountSearch: string
  activeInvestigationTab: 'accounts' | 'graph' | 'rings' | 'chains'
  sidebarOpen: boolean
}

type InvestigationAction =
  | { type: 'SELECT_ACCOUNT'; accountId: string | null }
  | { type: 'SELECT_NODE'; nodeId: string | null }
  | { type: 'SET_GRAPH_DEPTH'; depth: number }
  | { type: 'TOGGLE_EXPANDED_NODE'; nodeId: string }
  | { type: 'CLEAR_EXPANDED_NODES' }
  | { type: 'SET_RELATIONSHIP_FILTERS'; types: RelationshipType[] }
  | { type: 'SET_RISK_FILTER'; level: RiskLevel }
  | { type: 'SET_ACCOUNT_SEARCH'; term: string }
  | { type: 'SET_ACTIVE_TAB'; tab: 'accounts' | 'graph' | 'rings' | 'chains' }
  | { type: 'SET_SIDEBAR_OPEN'; open: boolean }
  | { type: 'RESET' }

const initialState: InvestigationState = {
  selectedAccountId: null,
  selectedNodeId: null,
  graphDepth: 2,
  expandedNodeIds: new Set(),
  relationshipFilters: new Set(['HAS_CARD', 'USES_DEVICE', 'HAS_PHONE', 'ACCESSED_FROM_IP']),
  riskFilter: null,
  accountSearch: '',
  activeInvestigationTab: 'accounts',
  sidebarOpen: true,
}

function investigationReducer(state: InvestigationState, action: InvestigationAction): InvestigationState {
  switch (action.type) {
    case 'SELECT_ACCOUNT':
      return {
        ...state,
        selectedAccountId: action.accountId,
        // Reset dependent state when account changes
        selectedNodeId: null,
        expandedNodeIds: new Set(),
        graphDepth: 2,
      }

    case 'SELECT_NODE':
      return { ...state, selectedNodeId: action.nodeId }

    case 'SET_GRAPH_DEPTH':
      return { ...state, graphDepth: Math.min(Math.max(action.depth, 1), 3) }

    case 'TOGGLE_EXPANDED_NODE': {
      const newSet = new Set(state.expandedNodeIds)
      if (newSet.has(action.nodeId)) {
        newSet.delete(action.nodeId)
      } else {
        newSet.add(action.nodeId)
      }
      return { ...state, expandedNodeIds: newSet }
    }

    case 'CLEAR_EXPANDED_NODES':
      return { ...state, expandedNodeIds: new Set() }

    case 'SET_RELATIONSHIP_FILTERS':
      return { ...state, relationshipFilters: new Set(action.types) }

    case 'SET_RISK_FILTER':
      return { ...state, riskFilter: action.level }

    case 'SET_ACCOUNT_SEARCH':
      return { ...state, accountSearch: action.term }

    case 'SET_ACTIVE_TAB':
      return { ...state, activeInvestigationTab: action.tab }

    case 'SET_SIDEBAR_OPEN':
      return { ...state, sidebarOpen: action.open }

    case 'RESET':
      return initialState

    default:
      return state
  }
}

interface InvestigationContextType {
  state: InvestigationState
  selectAccount: (accountId: string | null) => void
  selectNode: (nodeId: string | null) => void
  setGraphDepth: (depth: number) => void
  toggleExpandedNode: (nodeId: string) => void
  clearExpandedNodes: () => void
  setRelationshipFilters: (types: RelationshipType[]) => void
  setRiskFilter: (level: RiskLevel) => void
  setAccountSearch: (term: string) => void
  setActiveTab: (tab: 'accounts' | 'graph' | 'rings' | 'chains') => void
  setSidebarOpen: (open: boolean) => void
  resetInvestigation: () => void
}

const InvestigationContext = createContext<InvestigationContextType | null>(null)

interface InvestigationProviderProps {
  children: ReactNode
}

export const InvestigationProvider: React.FC<InvestigationProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(investigationReducer, initialState)

  const selectAccount = useCallback((accountId: string | null) => {
    dispatch({ type: 'SELECT_ACCOUNT', accountId })
  }, [])

  const selectNode = useCallback((nodeId: string | null) => {
    dispatch({ type: 'SELECT_NODE', nodeId })
  }, [])

  const setGraphDepth = useCallback((depth: number) => {
    dispatch({ type: 'SET_GRAPH_DEPTH', depth })
  }, [])

  const toggleExpandedNode = useCallback((nodeId: string) => {
    dispatch({ type: 'TOGGLE_EXPANDED_NODE', nodeId })
  }, [])

  const clearExpandedNodes = useCallback(() => {
    dispatch({ type: 'CLEAR_EXPANDED_NODES' })
  }, [])

  const setRelationshipFilters = useCallback((types: RelationshipType[]) => {
    dispatch({ type: 'SET_RELATIONSHIP_FILTERS', types })
  }, [])

  const setRiskFilter = useCallback((level: RiskLevel) => {
    dispatch({ type: 'SET_RISK_FILTER', level })
  }, [])

  const setAccountSearch = useCallback((term: string) => {
    dispatch({ type: 'SET_ACCOUNT_SEARCH', term })
  }, [])

  const setActiveTab = useCallback((tab: 'accounts' | 'graph' | 'rings' | 'chains') => {
    dispatch({ type: 'SET_ACTIVE_TAB', tab })
  }, [])

  const setSidebarOpen = useCallback((open: boolean) => {
    dispatch({ type: 'SET_SIDEBAR_OPEN', open })
  }, [])

  const resetInvestigation = useCallback(() => {
    dispatch({ type: 'RESET' })
  }, [])

  const value: InvestigationContextType = useMemo(
    () => ({
      state,
      selectAccount,
      selectNode,
      setGraphDepth,
      toggleExpandedNode,
      clearExpandedNodes,
      setRelationshipFilters,
      setRiskFilter,
      setAccountSearch,
      setActiveTab,
      setSidebarOpen,
      resetInvestigation,
    }),
    [
      state,
      selectAccount,
      selectNode,
      setGraphDepth,
      toggleExpandedNode,
      clearExpandedNodes,
      setRelationshipFilters,
      setRiskFilter,
      setAccountSearch,
      setActiveTab,
      setSidebarOpen,
      resetInvestigation,
    ]
  )

  return (
    <InvestigationContext.Provider value={value}>
      {children}
    </InvestigationContext.Provider>
  )
}

export const useInvestigation = (): InvestigationContextType => {
  const context = useContext(InvestigationContext)
  if (!context) {
    throw new Error('useInvestigation must be used within an InvestigationProvider')
  }
  return context
}
