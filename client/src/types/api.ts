// API DTO Types - Public API Contract
// These types represent the data transfer objects returned by the FastAPI backend.
// Frontend components must use these types exclusively.
// Database property names are NEVER exposed through these types.

// ============= Pagination DTOs =============

export interface PaginationMeta {
  cursor: string | null
  hasNextPage: boolean
  pageSize: number
}

export interface PaginatedResponse<T> extends PaginationMeta {
  items: T[]
}

// ============= Account DTOs =============

export interface AccountDTO {
  accountId: string
  displayName: string
  email?: string
  status: string
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  riskScore: number
  isKnownFraud: boolean
  createdAt?: string
}

export interface CardDTO {
  cardId: string
  cardNumber?: string
  cardType: string
  status: string
}

export interface SharedDeviceDTO {
  deviceId: string
  deviceName: string
  connectedAccountCount: number
}

export interface SharedPhoneDTO {
  phoneNumber: string
  connectedAccountCount: number
}

export interface SharedIPDTO {
  ipAddress: string
  connectedAccountCount: number
}

export interface AccountConnectionsDTO {
  accountId: string
  displayName: string
  cards: CardDTO[]
  sharedDevices: SharedDeviceDTO[]
  sharedPhones: SharedPhoneDTO[]
  sharedIPs: SharedIPDTO[]
}

// ============= Graph DTOs =============

export interface GraphNodeDTO {
  id: string
  type: 'ACCOUNT' | 'CARD' | 'DEVICE' | 'PHONE_NUMBER' | 'IP_ADDRESS' | 'TRANSACTION'
  label: string
  riskLevel?: string
  riskScore?: number
  isKnownFraud?: boolean
  metadata?: Record<string, unknown>
}

export interface GraphEdgeDTO {
  id: string
  source: string
  target: string
  relationship: 'HAS_CARD' | 'USES_DEVICE' | 'HAS_PHONE' | 'ACCESSED_FROM_IP' | 'TRANSACTED_WITH' | 'SHARED_DEVICE' | 'SHARED_PHONE' | 'SHARED_IP'
  weight?: number
}

export interface GraphResponseDTO {
  nodes: GraphNodeDTO[]
  edges: GraphEdgeDTO[]
  cursor?: string
  hasMoreConnections: boolean
}

// ============= Fraud Detection DTOs =============

export interface FraudRingDTO {
  ringId: string
  riskLevel: string
  riskScore: number
  memberCount: number
  knownFraudCount: number
  detectionReason: string
  accountIds: string[]
}

export interface MoneyMuleChainDTO {
  chainId: string
  riskLevel: string
  riskScore: number
  chainLength: number
  accountIds: string[]
  detectionReason: string
}

// ============= Dashboard DTOs =============

export interface DashboardStatsDTO {
  totalAccounts: number
  knownFraudAccounts: number
  detectedFraudRings: number
  mediumRiskAccounts: number
  highRiskAccounts: number
  criticalRiskAccounts: number
}

// ============= Type Guards =============

export function isAccountDTO(obj: unknown): obj is AccountDTO {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'accountId' in obj &&
    'displayName' in obj &&
    'riskLevel' in obj
  )
}

export function isGraphNodeDTO(obj: unknown): obj is GraphNodeDTO {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'type' in obj &&
    'label' in obj
  )
}

export function isGraphEdgeDTO(obj: unknown): obj is GraphEdgeDTO {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'source' in obj &&
    'target' in obj &&
    'relationship' in obj
  )
}

export function isPaginatedResponse<T>(obj: unknown): obj is PaginatedResponse<T> {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'items' in obj &&
    'cursor' in obj &&
    'hasNextPage' in obj
  )
}
