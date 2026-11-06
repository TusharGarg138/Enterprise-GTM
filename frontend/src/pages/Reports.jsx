import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout } from '../components/Layout'
import { LoadingState, ErrorState, EmptyState, ScoreBadge, StatusBadge } from '../components/ui'
import { getReports, getAccounts } from '../services/api'
import { FileText, Building2, Calendar } from 'lucide-react'

export default function Reports() {
  const navigate = useNavigate()
  const [reports, setReports] = useState([])
  const [accountsMap, setAccountsMap] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [reportsRes, accRes] = await Promise.all([
        getReports(100),
        getAccounts({ page_size: 100 })
      ])
      setReports(reportsRes?.data || [])
      const map = {}
      accRes?.data?.items?.forEach(a => { map[a.account_id] = a })
      setAccountsMap(map)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <Layout title="Account Intelligence Reports" subtitle="Historical multi-agent research generated profiles">
      {loading ? (
        <LoadingState message="Loading reports..." />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : reports.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No reports generated yet"
          description="Trigger research on any account to produce an evidence-backed intelligence report."
          action={<button className="btn-primary text-sm" onClick={() => navigate('/research')}>Create Research</button>}
        />
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#2a3348]">
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Account</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Score & Priority</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Model</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Status</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Generated At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#2a3348]">
              {reports.map((r) => {
                const acc = accountsMap[r.account_id]
                return (
                  <tr
                    key={r.report_id}
                    className="hover:bg-[#1e2535] cursor-pointer transition-colors"
                    onClick={() => navigate(`/accounts/${r.account_id}`)}
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-blue-900/30 border border-blue-800/30 flex items-center justify-center shrink-0">
                          <Building2 className="w-4 h-4 text-blue-400" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-200">{acc?.company_name || r.account_id}</p>
                          <p className="text-xs text-gray-500">{acc?.industry || 'Unknown Industry'}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <ScoreBadge score={r.account_score} category={r.score_category} />
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-xs text-gray-400 font-mono bg-[#1e2535] px-2 py-1 rounded">
                        {r.model_name || 'gemini-2.0-flash'}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-xs text-gray-400 flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-gray-500" />
                        {r.generated_at ? new Date(r.generated_at).toLocaleString() : '—'}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  )
}
