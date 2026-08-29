import React from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, TrendingUp, Users, Loader } from 'lucide-react'
import { MetricCard, ErrorState } from '../components/common'
import { useDashboard } from '../hooks/useDashboard'
import { useRiskDistribution } from '../hooks/useRiskDistribution'
import { useTopSharedDevices } from '../hooks/useTopSharedDevices'
import { useTopSharedIPs } from '../hooks/useTopSharedIPs'
import { useClosestToFraud } from '../hooks/useClosestToFraud'

const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const { stats, isLoading, error, refresh } = useDashboard()
  const { distribution } = useRiskDistribution()
  const { devices, isLoading: devicesLoading } = useTopSharedDevices()
  const { ips, isLoading: ipsLoading } = useTopSharedIPs()
  const { accounts: closestToFraudAccounts, isLoading: fraudLoading } = useClosestToFraud()

  if (error && !stats) {
    return (
      <ErrorState
        title="Failed to Load Dashboard"
        message={error.message}
        onRetry={refresh}
      />
    )
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Fraud Investigation Dashboard</h1>
        <p className="text-slate-600">
          Real-time overview of suspicious accounts, fraud rings, and money-mule networks
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          label="Total Accounts"
          value={stats?.totalAccounts || 0}
          icon={<Users />}
          loading={isLoading}
        />
        <MetricCard
          label="Known Fraud"
          value={stats?.knownFraudAccounts || 0}
          icon={<AlertCircle />}
          loading={isLoading}
        />
        <MetricCard
          label="Fraud Rings"
          value={stats?.detectedFraudRings || 0}
          icon={<Users />}
          loading={isLoading}
        />
        <MetricCard
          label="High Risk"
          value={stats?.highRiskAccounts || 0}
          icon={<TrendingUp />}
          loading={isLoading}
        />
        <MetricCard
          label="Critical Risk"
          value={stats?.criticalRiskAccounts || 0}
          icon={<AlertCircle className="text-red-600" />}
          loading={isLoading}
        />
      </div>

      {/* Risk Distribution Chart */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 md:p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-6">Risk Distribution</h2>
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loader className="w-6 h-6 animate-spin text-blue-600" />
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 auto-rows-max">
            {distribution.map((item) => (
              <div key={item.label} className="text-center flex flex-col items-center justify-start">
                <div className="mb-4 w-full flex justify-center">
                  <div className="relative w-16 h-16 md:w-20 md:h-20 flex-shrink-0">
                    <div className={`absolute inset-0 rounded-full ${item.color} opacity-20`} />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-base md:text-xl font-bold text-slate-900 text-center px-1">{item.count}</span>
                    </div>
                  </div>
                </div>
                <p className="text-xs md:text-sm font-medium text-slate-600 break-words max-w-full">{item.label}</p>
                <p className="text-xs text-slate-500">{item.percentage}%</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Suspicious Connections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">📱 Top Shared Devices</h3>
          {devicesLoading ? (
            <div className="flex items-center justify-center h-32">
              <Loader className="w-6 h-6 animate-spin text-blue-600" />
            </div>
          ) : devices.length === 0 ? (
            <p className="text-sm text-slate-500">No suspicious devices found</p>
          ) : (
            <div className="space-y-3">
              {devices.map((device) => (
                <div key={device.deviceId} className="flex justify-between items-center p-3 bg-slate-50 rounded">
                  <span className="text-sm font-medium text-slate-900">{device.deviceName}</span>
                  <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-semibold">
                    {device.connectedAccountCount} accounts
                  </span>
                </div>
              ))}
              <p className="text-xs text-slate-500 mt-4">
                Devices used by multiple accounts may indicate coordinated fraud activity
              </p>
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">🌐 Top Shared IPs</h3>
          {ipsLoading ? (
            <div className="flex items-center justify-center h-32">
              <Loader className="w-6 h-6 animate-spin text-blue-600" />
            </div>
          ) : ips.length === 0 ? (
            <p className="text-sm text-slate-500">No suspicious IPs found</p>
          ) : (
            <div className="space-y-3">
              {ips.map((ip) => (
                <div key={ip.ipAddress} className="flex justify-between items-center p-3 bg-slate-50 rounded">
                  <span className="text-sm font-medium text-slate-900">{ip.ipAddress}</span>
                  <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-semibold">
                    {ip.connectedAccountCount} accounts
                  </span>
                </div>
              ))}
              <p className="text-xs text-slate-500 mt-4">
                Multiple accounts from the same IP may indicate shared infrastructure
              </p>
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">⚠️ Closest to Fraud</h3>
          {fraudLoading ? (
            <div className="flex items-center justify-center h-32">
              <Loader className="w-6 h-6 animate-spin text-blue-600" />
            </div>
          ) : closestToFraudAccounts.length === 0 ? (
            <p className="text-sm text-slate-500">No high-risk accounts found</p>
          ) : (
            <div className="space-y-3">
              {closestToFraudAccounts.map((account) => (
                <div key={account.accountId} className="flex justify-between items-center p-3 bg-slate-50 rounded">
                  <span className="text-sm font-medium text-slate-900">{account.displayName}</span>
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${
                    account.hopsToFraud === 0 
                      ? 'bg-red-100 text-red-700' 
                      : 'bg-orange-100 text-orange-700'
                  }`}>
                    {account.hopsToFraud} hop{account.hopsToFraud !== 1 ? 's' : ''}
                  </span>
                </div>
              ))}
              <p className="text-xs text-slate-500 mt-4">
                Accounts directly connected to known fraud are high priority
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Call to Action */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200 p-8">
        <div className="flex items-start gap-6">
          <div className="text-4xl">🔍</div>
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-slate-900 mb-2">Start Investigation</h2>
            <p className="text-slate-600 mb-6">
              Explore suspicious accounts, fraud rings, and money-mule networks in detail. Click
              below to access the account investigation tool.
            </p>
            <button
              onClick={() => navigate('/accounts')}
              className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
            >
              Explore Accounts
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
