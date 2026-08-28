import React from 'react'
import { getRiskLevelColor, capitalizeFirstLetter } from '../../utils/formatting'

interface RiskBadgeProps {
  level: string
  size?: 'sm' | 'md' | 'lg'
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, size = 'md' }) => {
  const sizeClasses = {
    sm: 'px-2 py-1 text-xs font-medium',
    md: 'px-3 py-1.5 text-sm font-medium',
    lg: 'px-4 py-2 text-base font-semibold',
  }

  return (
    <span
      className={`
        inline-flex items-center rounded-full border
        ${sizeClasses[size]}
        ${getRiskLevelColor(level)}
      `}
    >
      {capitalizeFirstLetter(level)}
    </span>
  )
}

interface RiskScoreProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
}

export const RiskScore: React.FC<RiskScoreProps> = ({ score, size = 'md' }) => {
  const getRiskColor = () => {
    if (score >= 75) return 'text-red-600'
    if (score >= 50) return 'text-orange-600'
    if (score >= 30) return 'text-yellow-600'
    return 'text-green-600'
  }

  const sizeClasses = {
    sm: 'text-lg font-semibold',
    md: 'text-2xl font-bold',
    lg: 'text-4xl font-bold',
  }

  return (
    <div className={`${getRiskColor()} ${sizeClasses[size]}`}>
      {Math.round(score)}
      <span className="text-sm font-normal opacity-75"> / 100</span>
    </div>
  )
}

interface MetricCardProps {
  label: string
  value: string | number
  icon?: React.ReactNode
  loading?: boolean
}

export const MetricCard: React.FC<MetricCardProps> = ({ label, value, icon, loading }) => {
  if (loading) {
    return (
      <div className="bg-white rounded-lg p-6 border border-slate-200">
        <div className="animate-shimmer h-4 w-20 mb-3 rounded" />
        <div className="animate-shimmer h-8 w-32 rounded" />
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg p-6 border border-slate-200 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-slate-600 text-sm font-medium">{label}</p>
          <p className="text-slate-900 text-2xl font-bold mt-2">{value}</p>
        </div>
        {icon && <div className="text-blue-600 text-2xl">{icon}</div>}
      </div>
    </div>
  )
}

interface LoadingSkeletonProps {
  rows?: number
  columns?: number
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ rows = 3, columns = 4 }) => {
  return (
    <div className="space-y-4">
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={rowIdx} className="flex gap-4">
          {Array.from({ length: columns }).map((_, colIdx) => (
            <div
              key={colIdx}
              className="flex-1 h-12 bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 rounded animate-shimmer"
            />
          ))}
        </div>
      ))}
    </div>
  )
}

interface EmptyStateProps {
  message: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  icon?: React.ReactNode
}

export const EmptyState: React.FC<EmptyStateProps> = ({ message, description, action, icon }) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 bg-slate-50 rounded-lg">
      {icon && <div className="text-slate-400 text-5xl mb-4">{icon}</div>}
      <h3 className="text-lg font-semibold text-slate-900 mb-2">{message}</h3>
      {description && <p className="text-slate-600 text-sm mb-6">{description}</p>}
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}

interface ErrorStateProps {
  title: string
  message: string
  onRetry?: () => void
  details?: string
}

export const ErrorState: React.FC<ErrorStateProps> = ({ title, message, onRetry, details }) => {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-6">
      <div className="flex gap-4">
        <div className="text-red-600 text-2xl flex-shrink-0">⚠️</div>
        <div className="flex-1">
          <h3 className="text-red-900 font-semibold mb-1">{title}</h3>
          <p className="text-red-800 text-sm mb-2">{message}</p>
          {details && <p className="text-red-700 text-xs font-mono mb-4 opacity-75">{details}</p>}
          {onRetry && (
            <button
              onClick={onRetry}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors text-sm font-medium"
            >
              Try Again
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

interface StatusBadgeProps {
  status: string
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const getStatusColor = (s: string) => {
    switch (s?.toUpperCase()) {
      case 'ACTIVE':
        return 'bg-green-100 text-green-800'
      case 'SUSPENDED':
        return 'bg-red-100 text-red-800'
      case 'INACTIVE':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-slate-100 text-slate-800'
    }
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(status)}`}>
      {status}
    </span>
  )
}
