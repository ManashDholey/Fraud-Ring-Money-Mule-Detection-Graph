import axios, { AxiosInstance } from 'axios'
import {
  AccountDTO,
  PaginatedResponse,
  AccountConnectionsDTO,
  GraphResponseDTO,
  FraudRingDTO,
  MoneyMuleChainDTO,
  DashboardStatsDTO,
} from '../types/api'

/**
 * API Service Layer
 * Provides typed methods for all backend API calls.
 * Manages cursor pagination internally.
 * Returns DTO types exclusively - never database properties.
 */
class APIService {
  private client: AxiosInstance
  private requestTimestamps: Map<string, number[]> = new Map() // Track request times per endpoint
  private readonly MAX_REQUESTS_PER_MINUTE = 100
  private readonly RATE_LIMIT_WINDOW_MS = 60000 // 1 minute

  constructor() {
    const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      response => response,
      error => {
        console.error('API Error:', error)
        throw error
      }
    )
  }

  /**
   * Check and enforce rate limiting per endpoint.
   * Logs warning if limit is approached to catch runaway request loops early.
   * @param endpoint API endpoint being called
   */
  private checkRateLimit(endpoint: string) {
    const now = Date.now()
    
    if (!this.requestTimestamps.has(endpoint)) {
      this.requestTimestamps.set(endpoint, [])
    }
    
    const timestamps = this.requestTimestamps.get(endpoint)!
    
    // Remove timestamps older than the rate limit window
    while (timestamps.length > 0 && timestamps[0] < now - this.RATE_LIMIT_WINDOW_MS) {
      timestamps.shift()
    }
    
    // Add current timestamp
    timestamps.push(now)
    
    // Warn if approaching limit (80% = 80 requests per minute)
    if (timestamps.length > this.MAX_REQUESTS_PER_MINUTE * 0.8) {
      console.warn(
        `⚠️ Rate limit warning: ${timestamps.length} requests to ${endpoint} in the last minute. ` +
        `Limit is ${this.MAX_REQUESTS_PER_MINUTE}/min. This may indicate a request loop bug.`
      )
    }
  }

  // ============= Accounts API =============

  /**
   * Search accounts with cursor pagination.
   * @param query Optional search term
   * @param limit Items per page (default: 25, max: 100)
   * @param cursor Opaque cursor from previous response
   * @returns Paginated AccountDTOs
   */
  async searchAccounts(
    query?: string,
    limit = 25,
    cursor?: string
  ): Promise<PaginatedResponse<AccountDTO>> {
    this.checkRateLimit('/accounts')
    
    // Build params conditionally: only include query if it's not empty
    const params: Record<string, string | number | undefined> = {
      limit: Math.min(limit, 100),
    }

    // Only include query if it's a non-empty string (after trimming)
    if (query && query.trim()) {
      params.query = query.trim()
    }

    // Only include cursor if provided
    if (cursor) {
      params.cursor = cursor
    }

    const response = await this.client.get<PaginatedResponse<AccountDTO>>('/accounts', {
      params,
    })
    return response.data
  }

  /**
   * Get single account details.
   * @param accountId Account identifier
   * @returns AccountDTO
   */
  async getAccountDetails(accountId: string): Promise<AccountDTO> {
    const response = await this.client.get<AccountDTO>(`/accounts/${accountId}`)
    return response.data
  }

  /**
   * Get account with all connections.
   * @param accountId Account identifier
   * @returns AccountConnectionsDTO
   */
  async getAccountConnections(accountId: string): Promise<AccountConnectionsDTO> {
    const response = await this.client.get<AccountConnectionsDTO>(
      `/accounts/${accountId}/connections`
    )
    return response.data
  }

  // ============= Graph Visualization API =============

  /**
   * Get account graph neighborhood.
   * @param accountId Account identifier
   * @param depth Traversal depth (1-3)
   * @returns GraphResponseDTO with nodes and edges
   */
  async getAccountGraph(accountId: string, depth = 2): Promise<GraphResponseDTO> {
    const response = await this.client.get<GraphResponseDTO>(
      `/accounts/${accountId}/graph`,
      {
        params: { depth: Math.min(depth, 3) },
      }
    )
    return response.data
  }

  /**
   * Expand graph to additional connections (lazy loading).
   * @param accountId Account identifier
   * @param cursor Cursor from previous response
   * @param depth Traversal depth
   * @returns GraphResponseDTO with new nodes and edges
   */
  async expandAccountGraph(
    accountId: string,
    cursor: string,
    depth = 2
  ): Promise<GraphResponseDTO> {
    const response = await this.client.get<GraphResponseDTO>(
      `/accounts/${accountId}/graph`,
      {
        params: { depth: Math.min(depth, 3), cursor },
      }
    )
    return response.data
  }

  // ============= Fraud Detection API =============

  /**
   * Get detected fraud rings.
   * @param limit Items per page
   * @param cursor Pagination cursor
   * @returns Paginated fraud rings
   */
  async getFraudRings(
    limit = 25,
    cursor?: string
  ): Promise<PaginatedResponse<FraudRingDTO>> {
    this.checkRateLimit('/networks/fraud-rings')
    
    const response = await this.client.get<PaginatedResponse<FraudRingDTO>>(
      '/networks/fraud-rings',
      {
        params: {
          limit: Math.min(limit, 100),
          cursor,
        },
      }
    )
    return response.data
  }

  /**
   * Get detected money-mule chains.
   * @param limit Items per page
   * @param cursor Pagination cursor
   * @returns Paginated money-mule chains
   */
  async getMoneyMuleChains(
    limit = 25,
    cursor?: string
  ): Promise<PaginatedResponse<MoneyMuleChainDTO>> {
    const response = await this.client.get<PaginatedResponse<MoneyMuleChainDTO>>(
      '/networks/money-mule-chains',
      {
        params: {
          limit: Math.min(limit, 100),
          cursor,
        },
      }
    )
    return response.data
  }

  /**
   * Get suspicious devices (shared across multiple accounts).
   * @returns List of suspicious device networks
   */
  async getSuspiciousDevices(): Promise<{ device_networks: any[]; network_count: number }> {
    const response = await this.client.get<{ device_networks: any[]; network_count: number }>(
      '/networks/suspicious-devices'
    )
    return response.data
  }

  /**
   * Get suspicious IPs (shared across multiple accounts).
   * @returns List of suspicious IP networks
   */
  async getSuspiciousIPs(): Promise<{ ip_networks: any[]; network_count: number }> {
    const response = await this.client.get<{ ip_networks: any[]; network_count: number }>(
      '/networks/suspicious-ips'
    )
    return response.data
  }

  /**
   * Get detected money-mule chains.
   * Chains show fund transfer patterns through multiple accounts.
   * @param limit Items per page
   * @param cursor Pagination cursor
   * @returns Paginated money-mule chains
   */
  async getMoneyMuleChainsTransactions(
    limit = 25,
    cursor?: string
  ): Promise<PaginatedResponse<MoneyMuleChainDTO>> {
    const response = await this.client.get<PaginatedResponse<MoneyMuleChainDTO>>(
      '/networks/money-mule-chains',
      {
        params: {
          limit: Math.min(limit, 100),
          cursor,
        },
      }
    )
    return response.data
  }

  // ============= Health API =============

  /**
   * Get system health status.
   * @returns Health status
   */
  async getHealth(): Promise<{ status: string; database: string }> {
    const response = await this.client.get<{ status: string; database: string }>(
      '/health'
    )
    return response.data
  }

  // ============= Legacy API Methods (Backward Compatibility) =============
  
  /**
   * Get dashboard metrics.
   * Backend returns camelCase via Pydantic v2 ConfigDict alias_generator.
   * @returns Dashboard statistics DTO
   */
  async getDashboard(): Promise<DashboardStatsDTO> {
    const response = await this.client.get<DashboardStatsDTO>('/dashboard')
    return response.data
  }

  /**
   * Test connection to backend.
   * @deprecated Use getHealth instead
   */
  async testConnection(): Promise<any> {
    const response = await this.client.get('/test-connection')
    return response.data
  }

  /**
   * Get account risk score.
   * @deprecated Risk score now included in AccountDTO
   */
  async getAccountRiskScore(accountId: string): Promise<any> {
    const account = await this.getAccountDetails(accountId)
    return { risk_score: account.riskScore, account_id: accountId }
  }

  /**
   * Get risk explanation.
   * @deprecated Risk information in AccountDTO and connections
   */
  async getRiskExplanation(accountId: string): Promise<any> {
    const connections = await this.getAccountConnections(accountId)
    return { account_id: accountId, explanation: 'See account connections', connections }
  }
}

// Singleton instance
export const apiService = new APIService()

// Backward compatibility
export const apiClient = apiService

export default apiService
