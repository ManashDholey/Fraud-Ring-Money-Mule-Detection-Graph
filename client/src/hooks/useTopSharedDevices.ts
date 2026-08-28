import { useState, useEffect, useRef } from 'react'
import { apiClient } from '../services/api'

export interface TopSharedDevice {
  deviceId: string
  deviceName: string
  connectedAccountCount: number
}

export interface UseTopSharedDevicesResult {
  devices: TopSharedDevice[]
  isLoading: boolean
  error: Error | null
  refetch: () => void
}

/**
 * Hook for fetching top shared devices.
 * Devices used by multiple accounts may indicate coordinated fraud activity.
 */
export function useTopSharedDevices(): UseTopSharedDevicesResult {
  const [devices, setDevices] = useState<TopSharedDevice[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const abortControllerRef = useRef<AbortController>(new AbortController())

  const fetchDevices = async () => {
    setIsLoading(true)
    setError(null)
    abortControllerRef.current?.abort()
    abortControllerRef.current = new AbortController()

    try {
      const response = await apiClient.getSuspiciousDevices()
      
      // Parse response and transform to TopSharedDevice format
      const transformedDevices: TopSharedDevice[] = (response.device_networks || [])
        .filter((d: any) => !d.error)
        .map((d: any) => ({
          deviceId: d.device_id || d.id || `device_${Math.random()}`,
          deviceName: d.device_name || d.name || 'Unknown Device',
          connectedAccountCount: d.user_count || d.account_count || d.connected_accounts || 0,
        }))
        .sort((a: TopSharedDevice, b: TopSharedDevice) => b.connectedAccountCount - a.connectedAccountCount)
        .slice(0, 5) // Top 5 only

      setDevices(transformedDevices)
    } catch (err) {
      if (err instanceof Error && err.message !== 'Aborted') {
        setError(err)
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchDevices()
    return () => abortControllerRef.current?.abort()
  }, [])

  return {
    devices,
    isLoading,
    error,
    refetch: fetchDevices,
  }
}
