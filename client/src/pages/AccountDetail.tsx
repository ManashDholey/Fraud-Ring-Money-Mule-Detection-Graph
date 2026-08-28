import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  AlertCircle,
  CheckCircle,
  Smartphone,
  Phone,
  Wifi,
} from 'lucide-react'
import {
  RiskBadge,
  RiskScore,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  StatusBadge,
} from '../components/common'
import { useAccountDetails } from '../hooks/useAccountDetails'
import {
  maskAccountNumber,
  maskPhoneNumber,
  maskIPAddress,
} from '../utils/formatting'

const AccountDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { account, connections, isLoading, error, refresh } = useAccountDetails(id ?? null)

  if (error) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => navigate('/accounts')}
          className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:text-blue-700"
        >
          <ArrowLeft size={20} />
          Back to Accounts
        </button>
        <ErrorState
          title="Failed to Load Account"
          message={error.message}
          onRetry={refresh}
        />
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => navigate('/accounts')}
          className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:text-blue-700"
        >
          <ArrowLeft size={20} />
          Back to Accounts
        </button>
        <LoadingSkeleton rows={4} columns={3} />
      </div>
    )
  }

  if (!account || !connections) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => navigate('/accounts')}
          className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:text-blue-700"
        >
          <ArrowLeft size={20} />
          Back to Accounts
        </button>
        <EmptyState
          message="Account not found"
          description="The requested account could not be loaded"
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={() => navigate('/accounts')}
        className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:text-blue-700 font-medium"
      >
        <ArrowLeft size={20} />
        Back to Accounts
      </button>

      {/* Account Summary */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-slate-600 font-medium mb-2">Customer Name</p>
            <p className="text-xl font-bold text-slate-900">{account.displayName}</p>
          </div>
          <div>
            <p className="text-sm text-slate-600 font-medium mb-2">Account ID</p>
            <p className="text-xl font-mono text-slate-600">{maskAccountNumber(account.accountId)}</p>
          </div>
          <div>
            <p className="text-sm text-slate-600 font-medium mb-2">Status</p>
            <StatusBadge status={account.status || 'ACTIVE'} />
          </div>
        </div>
      </div>

      {/* Risk Summary */}
      <div className={`rounded-lg border p-6 ${
        account.riskLevel === 'CRITICAL'
          ? 'bg-red-50 border-red-200'
          : account.riskLevel === 'HIGH'
          ? 'bg-orange-50 border-orange-200'
          : account.riskLevel === 'MEDIUM'
          ? 'bg-yellow-50 border-yellow-200'
          : 'bg-green-50 border-green-200'
      }`}>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div>
            <p className="text-sm text-slate-600 font-medium mb-3">Risk Score</p>
            <RiskScore score={account.riskScore} size="md" />
          </div>
          <div>
            <p className="text-sm text-slate-600 font-medium mb-3">Risk Level</p>
            <RiskBadge level={account.riskLevel} size="lg" />
          </div>
          <div>
            <p className="text-sm text-slate-600 font-medium mb-2">Known Fraud</p>
            {account.isKnownFraud ? (
              <div className="flex items-center gap-2 text-red-700 font-semibold">
                <AlertCircle size={20} />
                YES
              </div>
            ) : (
              <div className="flex items-center gap-2 text-green-700 font-semibold">
                <CheckCircle size={20} />
                NO
              </div>
            )}
          </div>
          <div>
            <p className="text-sm text-slate-600 font-medium mb-2">Connected Accounts</p>
            <p className="text-2xl font-bold text-slate-900">
              {(connections.sharedDevices?.length || 0) + (connections.sharedPhones?.length || 0) + (connections.sharedIPs?.length || 0)}
            </p>
          </div>
        </div>
      </div>

      {/* Account Connections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Payment Cards */}
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <AlertCircle size={20} />
            Payment Cards
          </h3>
          {(connections.cards?.length || 0) === 0 ? (
            <p className="text-slate-600 text-sm">No cards found</p>
          ) : (
            <div className="space-y-3">
              {connections.cards?.map((card) => (
                <div
                  key={card.cardId}
                  className="p-3 rounded border bg-slate-50 border-slate-200"
                >
                  <p className="font-medium text-slate-900 text-sm">{card.cardType}</p>
                  <p className="text-xs text-slate-600 mt-1 font-mono">{maskAccountNumber(card.cardNumber || '')}</p>
                  <p className="text-xs text-slate-500 mt-1">Status: {card.status}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Shared Devices */}
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <Smartphone size={20} />
            Shared Devices
          </h3>
          {(connections.sharedDevices?.length || 0) === 0 ? (
            <p className="text-slate-600 text-sm">No shared devices</p>
          ) : (
            <div className="space-y-3">
              {connections.sharedDevices?.map((device) => (
                <div
                  key={device.deviceId}
                  className="p-3 rounded border bg-orange-50 border-orange-200"
                >
                  <p className="font-medium text-slate-900 text-sm">{device.deviceName}</p>
                  <p className="text-xs text-slate-600 mt-1">{device.connectedAccountCount} connected account(s)</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Shared Phone Numbers */}
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <Phone size={20} />
            Shared Phones
          </h3>
          {(connections.sharedPhones?.length || 0) === 0 ? (
            <p className="text-slate-600 text-sm">No shared phone numbers</p>
          ) : (
            <div className="space-y-3">
              {connections.sharedPhones?.map((phone) => (
                <div
                  key={phone.phoneNumber}
                  className="p-3 rounded border bg-yellow-50 border-yellow-200"
                >
                  <p className="font-medium text-slate-900 text-sm">{maskPhoneNumber(phone.phoneNumber)}</p>
                  <p className="text-xs text-slate-600 mt-1">{phone.connectedAccountCount} connected account(s)</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Shared IPs */}
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <Wifi size={20} />
            Shared IPs
          </h3>
          {(connections.sharedIPs?.length || 0) === 0 ? (
            <p className="text-slate-600 text-sm">No shared IP addresses</p>
          ) : (
            <div className="space-y-3">
              {connections.sharedIPs?.map((ip) => (
                <div
                  key={ip.ipAddress}
                  className="p-3 rounded border bg-purple-50 border-purple-200"
                >
                  <p className="font-medium text-slate-900 text-sm font-mono">{maskIPAddress(ip.ipAddress)}</p>
                  <p className="text-xs text-slate-600 mt-1">{ip.connectedAccountCount} connected account(s)</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Investigation Guide */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-4">💡 Investigation Guide</h3>
        <ul className="space-y-3 text-slate-700">
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold">1.</span>
            <span>Check the risk level and score above to assess the account's threat level</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold">2.</span>
            <span>Review shared devices, phones, and IPs to identify coordinated activity</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold">3.</span>
            <span>Visit the Graph Explorer for a visual representation of connections</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold">4.</span>
            <span>Review Fraud Rings to see if this account is part of a larger network</span>
          </li>
        </ul>
      </div>
    </div>
  )
}

export default AccountDetail
