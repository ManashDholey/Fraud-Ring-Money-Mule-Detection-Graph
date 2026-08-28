// Utility functions for fraud detection UI

export const getRiskLevelColor = (riskLevel: string): string => {
  switch (riskLevel?.toUpperCase()) {
    case 'LOW':
      return 'bg-green-100 text-green-800 border-green-300'
    case 'MEDIUM':
      return 'bg-yellow-100 text-yellow-800 border-yellow-300'
    case 'HIGH':
      return 'bg-orange-100 text-orange-800 border-orange-300'
    case 'CRITICAL':
      return 'bg-red-100 text-red-800 border-red-300'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-300'
  }
}

export const getRiskLevelBgColor = (riskLevel: string): string => {
  switch (riskLevel?.toUpperCase()) {
    case 'LOW':
      return 'bg-green-50'
    case 'MEDIUM':
      return 'bg-yellow-50'
    case 'HIGH':
      return 'bg-orange-50'
    case 'CRITICAL':
      return 'bg-red-50'
    default:
      return 'bg-gray-50'
  }
}

export const getRiskLevelTextColor = (riskLevel: string): string => {
  switch (riskLevel?.toUpperCase()) {
    case 'LOW':
      return 'text-green-700'
    case 'MEDIUM':
      return 'text-yellow-700'
    case 'HIGH':
      return 'text-orange-700'
    case 'CRITICAL':
      return 'text-red-700'
    default:
      return 'text-gray-700'
  }
}

export const maskAccountNumber = (accountId: string): string => {
  if (!accountId || accountId.length < 4) return accountId
  return `•••${accountId.slice(-4)}`
}

export const maskCardNumber = (cardNumber?: string): string => {
  if (!cardNumber || cardNumber.length < 4) return cardNumber || '••••'
  return `•••${cardNumber.slice(-4)}`
}

export const maskPhoneNumber = (phone: string): string => {
  if (!phone) return '••••'
  // For US numbers like +1-555-0001, show last 4 digits
  const lastFour = phone.slice(-4)
  return `•••${lastFour}`
}

export const maskIPAddress = (ip: string): string => {
  if (!ip) return '••••'
  // Show last octet only
  const parts = ip.split('.')
  if (parts.length === 4) {
    return `•••.•••.•••.${parts[3]}`
  }
  return ip
}

export const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount)
}

export const formatDate = (dateString?: string): string => {
  if (!dateString) return 'Unknown'
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return 'Invalid date'
  }
}

export const formatDateTime = (dateString?: string): string => {
  if (!dateString) return 'Unknown'
  try {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return 'Invalid date'
  }
}

export const getRiskScorePercentage = (score: number): number => {
  return Math.min(Math.max(Math.round((score / 100) * 100), 0), 100)
}

export const formatRiskScore = (score: number): string => {
  return `${Math.round(score)}/100`
}

export const truncateString = (str: string, maxLength: number): string => {
  if (!str || str.length <= maxLength) return str
  return `${str.slice(0, maxLength)}…`
}

export const capitalizeFirstLetter = (str: string): string => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}
