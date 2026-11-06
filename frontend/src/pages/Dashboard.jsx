import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout } from '../components/Layout'
import { StatCard, LoadingState, ErrorState, ScoreBadge, StatusBadge } from '../components/ui'
import { getAccounts, getReports, getHealth } from '../services/api'
import { Building2, TrendingUp, AlertTriangle, FileText, Activity } from 'lucide-react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const PRIORITY_COLORS = {
  'High Priority': '#10b981',
  'Medium Priority': '#f59e0b',
  'Low Priority': '#6b7280',
}

export default function Dashboard() {
  const [accounts, setAccounts] = useState([])
  const [reports, setReports] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [accsRes, reportsRes, healthRes] = await Promise.allSettled([
        getAccounts({ page_size: 100 }),
        getReports(10),
        getHealth(),
      ])

      if (accsRes.status === 'fulfilled') {
        setAccounts(accsRes.value?.data?.items || [])
      }
      if (reportsRes.status === 'fulfilled') {
        setReports(reportsRes.value?.data || [])
      }
      if (healthRes.status === 'fulfilled') {
        setHealth(healthRes.value)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const stats = {
    total: accounts.length,
    high: accounts.filter(a => a.score_category === 'High Priority').length,
    withOpps: accounts.filter(a => a.opportunity_count > 0).length,
    withRisks: accounts.filter(a => a.risk_flag).length,
    researched: accounts.filter(a => a.last_researched).length,
  }

  const priorityData = [
    { name: 'High Priority', value: accounts.filter(a => a.score_category === 'High Priority').length },
    { name: 'Medium Priority', value: accounts.filter(a => a.score_category === 'Medium Priority').length },
    { name: 'Low Priority', value: accounts.filter(a => a.score_category === 'Low Priority').length },
    { name: 'Unscored', value: accounts.filter(a => !a.score_category).length },
  ].filter(d => d.value > 0)

  if (loading) return <Layout title="Dashboard"><LoadingState message="Loading dashboard..." /></Layout>
  if (error) return <Layout title="Dashboard"><ErrorState message={error} onRetry={load} /></Layout>

  return (
    <Layout
      title="GTM Intelligence Dashboard"
      subtitle={health ? `${health.environment} · DB: ${health.database} · AI: ${health.gemini}` : ''}
    >
      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Accounts" value={stats.total} icon={Building2} color="blue" onClick={() => navigate('/accounts')} />
        <StatCard label="High Priority" value={stats.high} icon={TrendingUp} color="green" onClick={() => navigate('/accounts?score_category=High+Priority')} />
        <StatCard label="With Opportunities" value={stats.withOpps} icon={Activity} color="purple" onClick={() => navigate('/opportunities')} />
        <StatCard label="Researched" value={stats.researched} icon={FileText} color="yellow" onClick={() => navigate('/reports')} />
      </div>

      {/* Charts + Recent */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Priority Distribution */}
        <div className="card lg:col-span-1">
          <h3 className="text-sm font-semibold text-gray-200 mb-4">Priority Distribution</h3>
          {priorityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={priorityData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {priorityData.map((entry) => (
                    <Cell key={entry.name} fill={PRIORITY_COLORS[entry.name] || '#6b7280'} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#161b27', border: '1px solid #2a3348', borderRadius: 8, color: '#e5e7eb' }}
                />
                <Legend
                  iconSize={8}
                  formatter={(value) => <span className="text-xs text-gray-400">{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center py-16 text-gray-500 text-sm">No scored accounts yet</div>
          )}
        </div>

        {/* Recent Reports */}
        <div className="card lg:col-span-2">
          <h3 className="text-sm font-semibold text-gray-200 mb-4">Recent Research Reports</h3>
          {reports.length === 0 ? (
            <div className="text-center py-10 text-gray-500 text-sm">
              No reports yet. Research an account to get started.
            </div>
          ) : (
            <div className="space-y-2">
              {reports.map((report) => {
                const acc = accounts.find(a => a.account_id === report.account_id)
                return (
                  <div
                    key={report.report_id}
                    className="flex items-center justify-between p-3 rounded-lg bg-[#1e2535] hover:bg-[#242d3f] cursor-pointer transition-colors"
                    onClick={() => navigate(`/accounts/${report.account_id}`)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-blue-900/30 border border-blue-800/30 flex items-center justify-center">
                        <Building2 className="w-4 h-4 text-blue-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-200">
                          {acc?.company_name || report.account_id}
                        </p>
                        <p className="text-xs text-gray-500">
                          {report.generated_at
                            ? new Date(report.generated_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                            : 'Unknown date'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <ScoreBadge score={report.account_score} category={report.score_category} />
                      <StatusBadge status={report.status} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mt-6 card">
        <h3 className="text-sm font-semibold text-gray-200 mb-4">Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button className="btn-primary text-sm" onClick={() => navigate('/research')}>
            + Research New Account
          </button>
          <button className="btn-secondary text-sm" onClick={() => navigate('/ingest')}>
            Upload CRM Data
          </button>
          <button className="btn-secondary text-sm" onClick={() => navigate('/accounts')}>
            View All Accounts
          </button>
        </div>
      </div>
    </Layout>
  )
}
