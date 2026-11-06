import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout } from '../components/Layout'
import { LoadingState, ErrorState, EmptyState, ScoreBadge, Pagination } from '../components/ui'
import { getAccounts } from '../services/api'
import { Building2, Search, Filter } from 'lucide-react'

const INDUSTRIES = ['Technology', 'Finance', 'Healthcare', 'Retail', 'Manufacturing', 'Professional Services', 'Education', 'Media', 'Energy', 'Logistics']

export default function Accounts() {
  const [accounts, setAccounts] = useState([])
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [industry, setIndustry] = useState('')
  const [page, setPage] = useState(1)
  const navigate = useNavigate()

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getAccounts({ search, industry, page, page_size: 20 })
      setAccounts(res?.data?.items || [])
      setTotal(res?.data?.total || 0)
      setPages(res?.data?.pages || 1)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [search, industry, page])

  useEffect(() => { load() }, [load])

  const handleSearch = (e) => { setSearch(e.target.value); setPage(1) }

  return (
    <Layout title="Accounts" subtitle={`${total} total accounts`}>
      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search accounts..."
            className="input-field pl-10"
            value={search}
            onChange={handleSearch}
          />
        </div>
        <select
          className="input-field w-44"
          value={industry}
          onChange={e => { setIndustry(e.target.value); setPage(1) }}
        >
          <option value="">All Industries</option>
          {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
        </select>
        <button className="btn-primary text-sm" onClick={() => navigate('/research')}>
          + New Account
        </button>
      </div>

      {/* Table */}
      {loading ? (
        <LoadingState message="Loading accounts..." />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : accounts.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No accounts found"
          description="Research a company or upload CRM data to get started."
          action={<button className="btn-primary text-sm" onClick={() => navigate('/research')}>Research Account</button>}
        />
      ) : (
        <>
          <div className="card p-0 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#2a3348]">
                  <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Company</th>
                  <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Industry</th>
                  <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Score</th>
                  <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Opportunities</th>
                  <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Last Research</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2a3348]">
                {accounts.map((acc) => (
                  <tr
                    key={acc.account_id}
                    className="hover:bg-[#1e2535] cursor-pointer transition-colors"
                    onClick={() => navigate(`/accounts/${acc.account_id}`)}
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-blue-900/30 border border-blue-800/30 flex items-center justify-center shrink-0">
                          <Building2 className="w-4 h-4 text-blue-400" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-200">{acc.company_name}</p>
                          {acc.website && (
                            <p className="text-xs text-gray-500 truncate max-w-[180px]">{acc.website}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-sm text-gray-400">{acc.industry || '—'}</span>
                    </td>
                    <td className="px-5 py-4">
                      <ScoreBadge score={acc.account_score} category={acc.score_category} />
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-sm text-gray-400">{acc.opportunity_count || 0}</span>
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-sm text-gray-400">
                        {acc.last_researched
                          ? new Date(acc.last_researched).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                          : <span className="text-gray-600">Not yet</span>}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pages={pages} onPage={setPage} />
        </>
      )}
    </Layout>
  )
}
