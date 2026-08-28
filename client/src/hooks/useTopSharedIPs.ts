import { useState, useEffect, useRef } from 'react'
import { apiClient } from '../services/api'

export interface TopSharedIP {
  ipAddress: string
  connectedAccountCount: number
}

export interface UseTopSharedIPsResult {
  ips: TopSharedIP[]
  isLoading: boolean
  error: Error | null
  refetch: () => void
}

/**
 * Hook for fetching top shared IPs.
 * Multiple accounts from the same IP may indicate shared infrastructure or coordinated fraud.
 */
export function useTopSharedIPs(): UseTopSharedIPsResult {
  const [ips, setIPs] = useState<TopSharedIP[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const abortControllerRef = useRef<AbortController>(new AbortController())

  const fetchIPs = async () => {
    setIsLoading(true)
    setError(null)
    abortControllerRef.current?.abort()
    abortControllerRef.current = new AbortController()

    try {
      const response = await apiClient.getSuspiciousIPs()
      
      // Parse response and transform to TopSharedIP format
      const transformedIPs: TopSharedIP[] = (response.ip_networks || [])
        .filter((ip: any) => !ip.error)
        .map((ip: any) => ({
          ipAddress: ip.ip_address || ip.ip || 'Unknown IP',
          connectedAccountCount: ip.user_count || ip.account_count || ip.connected_accounts || 0,
        }))
        .sort((a: TopSharedIP, b: TopSharedIP) => b.connectedAccountCount - a.connectedAccountCount)
        .slice(0, 5) // Top 5 only

      setIPs(transformedIPs)
    } catch (err) {
      if (err instanceof Error && err.message !== 'Aborted') {
        setError(err)
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchIPs()
    return () => abortControllerRef.current?.abort()
  }, [])

  return {
    ips,
    isLoading,
    error,
    refetch: fetchIPs,
  }
}
