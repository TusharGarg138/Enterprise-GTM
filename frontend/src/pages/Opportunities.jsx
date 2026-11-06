import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout } from '../components/Layout'
import { LoadingState, ErrorState, EmptyState, ConfidenceBadge } from '../components/ui'
import { getOpportunities, getReports, getAccounts } from '../services/api'
import { TrendingUp, Building2, ExternalLink } from 'lucide-react'

export default function Opportunities() {
  const navigate = useNavigate()
  const [opportunities, setOpportunities] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterConfidence, setFilterConfidence] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      let allOpps = []
      try {
        const oppsRes = await getOpportunities({ limit: 200 })
        if (oppsRes?.data?.length) {
          allOpps = oppsRes.data.filter(o => o.opportunity_title)
        }
      } catch (e) {
        // Fallback to reports
      }

      if (allOpps.length === 0) {
        const [reportsRes, accountsRes] = await Promise.all([
          getReports(100),
          getAccounts({ page_size: 100 })
        ])

        const accMap = {}
        accountsRes?.data?.items?.forEach(a => { accMap[a.account_id] = a })

        reportsRes?.data?.forEach(r => {
          const opps = r.report_json?.opportunities || []
          opps.forEach(o => {
            allOpps.push({
              ...o,
              account_id: r.account_id,
              company_name: accMap[r.account_id]?.company_name || r.account_id,
              report_id: r.report_id
            })
          })
        })
      }

      setOpportunities(allOpps)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = filterConfidence
    ? opportunities.filter(o => o.confidence_level?.toLowerCase() === filterConfidence.toLowerCase())
    : opportunities

  return (
    <Layout title="Opportunities" subtitle={`${opportunities.length} total opportunities identified across accounts`}>
      <div className="flex gap-3 mb-6">
        <select
          className="input-field w-48"
          value={filterConfidence}
          onChange={e => setFilterConfidence(e.target.value)}
        >
          <option value="">All Confidence Levels</option>
          <option value="high">High Confidence</option>
          <option value="medium">Medium Confidence</option>
          <option value="low">Low Confidence</option>
        </select>
      </div>

      {loading ? (
        <LoadingState message="Aggregating opportunities..." />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={TrendingUp}
          title="No opportunities found"
          description="Run research on your accounts to detect evidence-backed opportunities."
          action={<button className="btn-primary text-sm" onClick={() => navigate('/research')}>Start Research</button>}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((opp, idx) => (
            <div key={idx} className="card flex flex-col justify-between">
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="text-xs font-semibold text-blue-400 flex items-center gap-1 cursor-pointer hover:underline" onClick={() => navigate(`/accounts/${opp.account_id}`)}>
                    <Building2 className="w-3.5 h-3.5" />
                    {opp.company_name}
                  </span>
                  <ConfidenceBadge level={opp.confidence_level} />
                </div>
                <h3 className="text-sm font-bold text-gray-100 mb-1">{opp.opportunity_title}</h3>
                <p className="text-xs text-gray-400 mb-3">{opp.description}</p>
                
                <div className="bg-[#1e2535] p-2.5 rounded-lg mb-3">
                  <p className="text-[11px] text-gray-500 font-semibold uppercase tracking-wider mb-1">Product Match</p>
                  <p className="text-xs text-blue-300 font-medium">{opp.relevant_product || 'General Solution'}</p>
                </div>

                {opp.validation_question && (
                  <div className="border-l-2 border-yellow-500/50 pl-2.5 py-1 mb-2">
                    <p className="text-[11px] text-yellow-400/80 font-medium">Validation Question:</p>
                    <p className="text-xs text-gray-300 italic">{opp.validation_question}</p>
                  </div>
                )}
              </div>

              {opp.recommended_action && (
                <div className="pt-3 border-t border-[#2a3348] mt-2">
                  <p className="text-[11px] text-gray-500 uppercase font-semibold">Recommended Action</p>
                  <p className="text-xs text-gray-300 mt-0.5">→ {opp.recommended_action}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}
