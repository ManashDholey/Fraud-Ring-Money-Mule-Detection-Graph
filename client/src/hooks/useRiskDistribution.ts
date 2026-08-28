import { useState, useEffect } from 'react'
import { useDashboard } from './useDashboard'

export interface RiskDistributionItem {
  label: string
  count: number
  color: string
  percentage: number
}

export interface UseRiskDistributionResult {
  distribution: RiskDistributionItem[]
  isLoading: boolean
  error: Error | null
}

/**
 * Hook for calculating risk distribution from dashboard stats.
 * Derives low risk, medium risk, high risk, and critical risk counts.
 */
export function useRiskDistribution(): UseRiskDistributionResult {
  const { stats, isLoading, error } = useDashboard()
  const [distribution, setDistribution] = useState<RiskDistributionItem[]>([])

  useEffect(() => {
    if (!stats) {
      return
    }

    // Calculate distribution based on actual data
    const totalAccounts = stats.totalAccounts || 1
    const criticalRisk = stats.criticalRiskAccounts || 0
    const highRisk = stats.highRiskAccounts || 0
    const mediumRisk = stats.mediumRiskAccounts || 0
    
    // Low risk: everything else
    const lowRisk = Math.max(0, totalAccounts - (mediumRisk + highRisk + criticalRisk))

    const items: RiskDistributionItem[] = [
      {
        label: 'Low Risk',
        count: lowRisk,
        color: 'bg-green-500',
        percentage: Math.round((lowRisk / totalAccounts) * 100),
      },
      {
        label: 'Medium Risk',
        count: mediumRisk,
        color: 'bg-yellow-500',
        percentage: Math.round((mediumRisk / totalAccounts) * 100),
      },
      {
        label: 'High Risk',
        count: highRisk,
        color: 'bg-orange-500',
        percentage: Math.round((highRisk / totalAccounts) * 100),
      },
      {
        label: 'Critical',
        count: criticalRisk,
        color: 'bg-red-500',
        percentage: Math.round((criticalRisk / totalAccounts) * 100),
      },
    ]

    setDistribution(items)
  }, [stats])

  return {
    distribution,
    isLoading,
    error,
  }
}
