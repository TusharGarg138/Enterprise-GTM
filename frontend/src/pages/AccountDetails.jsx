import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout } from '../components/Layout'
import {
  LoadingState, ErrorState, ScoreBadge, StatusBadge,
  ConfidenceBadge, SectionHeader, InfoRow
} from '../components/ui'
import { getAccount, getAccountReports, triggerResearch, getJobStatus, getReport } from '../services/api'
import { Building2, ArrowLeft, Play, RefreshCw, Users, Activity, TrendingUp, AlertTriangle, FileText, MessageSquare } from 'lucide-react'

function OpportunityCard({ opp }) {
  return (
    <div className="p-4 rounded-lg bg-[#1e2535] border border-[#2a3348]">
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-sm font-medium text-gray-200">{opp.opportunity_title}</p>
        <ConfidenceBadge level={opp.confidence_level} />
      </div>
      <p className="text-xs text-gray-400 mb-2">{opp.description}</p>
      <div className="flex items-center gap-2 mt-3">
        <span className="text-xs text-gray-500">Product:</span>
        <span className="text-xs text-blue-400">{opp.relevant_product}</span>
      </div>
      {opp.recommended_action && (
        <div className="mt-2 p-2 rounded bg-blue-900/20 border border-blue-800/30">
          <p className="text-xs text-blue-300">→ {opp.recommended_action}</p>
        </div>
      )}
    </div>
  )
}

function RiskCard({ risk }) {
  const severityClass = {
    high: 'border-red-800/50 bg-red-900/10',
    medium: 'border-yellow-800/50 bg-yellow-900/10',
    low: 'border-gray-700/50 bg-gray-800/10',
  }[risk.severity?.toLowerCase()] || 'border-gray-700/50'

  return (
    <div className={`p-4 rounded-lg border ${severityClass}`}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-sm font-medium text-gray-200">{risk.risk_description}</p>
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
          risk.severity === 'high' ? 'text-red-400' :
          risk.severity === 'medium' ? 'text-yellow-400' : 'text-gray-400'
        }`}>{risk.severity?.toUpperCase()}</span>
      </div>
      <p className="text-xs text-gray-500 mb-2 capitalize">{risk.risk_category?.replace('_', ' ')}</p>
      {risk.suggested_action && (
        <p className="text-xs text-gray-400">→ {risk.suggested_action}</p>
      )}
    </div>
  )
}

export default function AccountDetails() {
  const { accountId } = useParams()
  const navigate = useNavigate()
  const [account, setAccount] = useState(null)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [researching, setResearching] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const accRes = await getAccount(accountId)
      setAccount(accRes?.data)

      // Load latest report if exists
      const rptRes = await getAccountReports(accountId)
      const reports = rptRes?.data || []
      if (reports.length > 0) {
        const latestReport = await getReport(reports[0].report_id)
        setReport(latestReport?.data)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [accountId])

  useEffect(() => { load() }, [load])

  // Poll job status
  useEffect(() => {
    if (!jobId || jobStatus?.status === 'complete' || jobStatus?.status === 'failed') return
    const interval = setInterval(async () => {
      try {
        const res = await getJobStatus(jobId)
        const status = res?.data
        setJobStatus(status)
        if (status?.status === 'complete') {
          setResearching(false)
          load() // Reload to get new report
        } else if (status?.status === 'failed') {
          setResearching(false)
        }
      } catch {}
    }, 3000)
    return () => clearInterval(interval)
  }, [jobId, jobStatus, load])

  const handleResearch = async () => {
    setResearching(true)
    setJobStatus(null)
    try {
      const res = await triggerResearch(accountId)
      setJobId(res?.data?.job_id)
      setJobStatus({ status: 'queued' })
    } catch (err) {
      setResearching(false)
      alert(`Research failed: ${err.message}`)
    }
  }

  if (loading) return <Layout title="Account Details"><LoadingState /></Layout>
  if (error) return <Layout title="Account Details"><ErrorState message={error} onRetry={load} /></Layout>
  if (!account) return <Layout title="Account Details"><ErrorState message="Account not found." /></Layout>

  const reportData = report?.report_json || {}
  const opportunities = reportData.opportunities || []
  const risks = reportData.risks || []
  const strategy = reportData.strategy || {}
  const companyProfile = reportData.company_profile || {}
  const scoreData = reportData.account_score || account.account_score
  const outreachDraft = reportData.outreach_draft || {}

  const TABS = [
    { id: 'overview', label: 'Overview', icon: Building2 },
    { id: 'opportunities', label: `Opportunities (${opportunities.length})`, icon: TrendingUp },
    { id: 'risks', label: `Risks (${risks.length})`, icon: AlertTriangle },
    { id: 'strategy', label: 'Strategy', icon: FileText },
    { id: 'crm', label: 'CRM Activity', icon: Activity },
  ]

  return (
    <Layout title={account.company_name} subtitle={account.industry || 'Unknown Industry'}>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            className="p-2 rounded-lg bg-[#1e2535] hover:bg-[#2a3348] transition-colors"
            onClick={() => navigate('/accounts')}
          >
            <ArrowLeft className="w-4 h-4 text-gray-400" />
          </button>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-blue-900/30 border border-blue-800/30 flex items-center justify-center">
              <Building2 className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-100">{account.company_name}</h1>
              <p className="text-sm text-gray-400">{account.website || 'No website'}</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {report?.account_score && (
            <ScoreBadge
              score={report.account_score}
              category={report.score_category}
            />
          )}
          <button
            className={`btn-primary text-sm flex items-center gap-2 ${researching ? 'opacity-70' : ''}`}
            onClick={handleResearch}
            disabled={researching}
          >
            {researching ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {researching ? (jobStatus?.status || 'Starting...') : 'Run Research'}
          </button>
        </div>
      </div>

      {/* Research Status */}
      {researching && (
        <div className="mb-4 p-3 rounded-lg bg-blue-900/20 border border-blue-800/30 flex items-center gap-3">
          <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
          <p className="text-sm text-blue-300">
            Running multi-agent research workflow...
            {jobStatus?.status && ` (${jobStatus.status})`}
          </p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-[#1e2535] rounded-lg mb-6 overflow-x-auto">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-md text-sm whitespace-nowrap transition-colors ${
              activeTab === id
                ? 'bg-blue-600 text-white font-medium'
                : 'text-gray-400 hover:text-gray-200'
            }`}
            onClick={() => setActiveTab(id)}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <SectionHeader title="Company Profile" />
            <InfoRow label="Industry" value={account.industry} />
            <InfoRow label="Website" value={account.website} />
            <InfoRow label="Employees" value={account.employee_band} />
            {companyProfile.business_model && <InfoRow label="Business Model" value={companyProfile.business_model} />}
            {companyProfile.target_customers && <InfoRow label="Target Customers" value={companyProfile.target_customers} />}
            {account.company_description && (
              <div className="mt-3 pt-3 border-t border-[#2a3348]">
                <p className="text-xs text-gray-500 mb-1">Description</p>
                <p className="text-sm text-gray-300">{account.company_description}</p>
              </div>
            )}
          </div>

          {reportData.research_findings?.length > 0 && (
            <div className="card">
              <SectionHeader title="Key Research Findings" />
              <ul className="space-y-2">
                {reportData.research_findings.map((f, i) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-300">
                    <span className="text-blue-400 mt-0.5">•</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {scoreData && typeof scoreData === 'object' && scoreData.components && (
            <div className="card lg:col-span-2">
              <SectionHeader
                title="Account Score Breakdown"
                description={`Total: ${Math.round(scoreData.total_score)}/100 · ${scoreData.category}`}
              />
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {scoreData.components.map((comp) => (
                  <div key={comp.name} className="p-3 rounded-lg bg-[#1e2535]">
                    <p className="text-xs text-gray-500 mb-1">{comp.name}</p>
                    <p className="text-2xl font-bold text-gray-100">{Math.round(comp.raw_score)}</p>
                    <div className="mt-1 h-1 rounded-full bg-[#2a3348]">
                      <div
                        className="h-1 rounded-full bg-blue-500"
                        style={{ width: `${comp.raw_score}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-1.5">{comp.reasoning.substring(0, 60)}...</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'opportunities' && (
        <div>
          {opportunities.length === 0 ? (
            <div className="card text-center py-10 text-gray-500">
              {report ? 'No opportunities identified in the latest research.' : 'Run research to identify opportunities.'}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {opportunities.map((opp, i) => <OpportunityCard key={i} opp={opp} />)}
            </div>
          )}
        </div>
      )}

      {activeTab === 'risks' && (
        <div>
          {risks.length === 0 ? (
            <div className="card text-center py-10 text-gray-500">
              {report ? 'No significant risks identified.' : 'Run research to assess account risks.'}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {risks.map((risk, i) => <RiskCard key={i} risk={risk} />)}
            </div>
          )}
        </div>
      )}

      {activeTab === 'strategy' && (
        <div className="space-y-6">
          {!report ? (
            <div className="card text-center py-10 text-gray-500">Run research to generate account strategy.</div>
          ) : (
            <>
              {strategy.account_summary && (
                <div className="card">
                  <SectionHeader title="Account Summary" />
                  <p className="text-sm text-gray-300">{strategy.account_summary}</p>
                </div>
              )}

              {strategy.recommended_actions?.length > 0 && (
                <div className="card">
                  <SectionHeader title="Recommended Actions" />
                  <div className="space-y-3">
                    {strategy.recommended_actions.map((action, i) => (
                      <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-[#1e2535]">
                        <span className={`text-xs font-bold px-1.5 py-0.5 rounded mt-0.5 ${
                          action.priority === 'high' ? 'bg-red-900/50 text-red-400' :
                          action.priority === 'medium' ? 'bg-yellow-900/50 text-yellow-400' :
                          'bg-gray-800 text-gray-400'
                        }`}>{(action.priority || 'med').toUpperCase()}</span>
                        <div>
                          <p className="text-sm text-gray-200">{action.action}</p>
                          {action.timeline && <p className="text-xs text-gray-500 mt-0.5">{action.timeline}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {strategy.discovery_questions?.length > 0 && (
                <div className="card">
                  <SectionHeader title="Discovery Questions" />
                  <ul className="space-y-2">
                    {strategy.discovery_questions.map((q, i) => (
                      <li key={i} className="flex gap-2 text-sm text-gray-300">
                        <span className="text-blue-400 font-bold">{i + 1}.</span>
                        <span>{q}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {outreachDraft?.subject && (
                <div className="card">
                  <div className="flex items-center justify-between mb-4">
                    <SectionHeader title="AI-Generated Outreach Draft" description="Requires human review and approval before sending" />
                    <span className="text-xs text-yellow-400 bg-yellow-900/30 border border-yellow-800/50 px-2 py-1 rounded">Pending Approval</span>
                  </div>
                  <div className="space-y-3">
                    <div className="p-3 rounded bg-[#1e2535]">
                      <p className="text-xs text-gray-500 mb-1">Subject</p>
                      <p className="text-sm text-gray-200">{outreachDraft.subject}</p>
                    </div>
                    <div className="p-3 rounded bg-[#1e2535]">
                      <p className="text-xs text-gray-500 mb-2">Body</p>
                      <p className="text-sm text-gray-200 whitespace-pre-wrap">{outreachDraft.body}</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 mt-3">⚠ This outreach draft requires human review. No emails are sent automatically.</p>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {activeTab === 'crm' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="card">
            <SectionHeader title={`Contacts (${account.contacts?.length || 0})`} />
            {account.contacts?.length === 0 ? (
              <p className="text-sm text-gray-500">No contacts on record.</p>
            ) : (
              <div className="space-y-3">
                {account.contacts?.map((c) => (
                  <div key={c.contact_id} className="flex items-center gap-3 p-2 rounded bg-[#1e2535]">
                    <div className="w-8 h-8 rounded-full bg-purple-900/30 border border-purple-800/30 flex items-center justify-center shrink-0">
                      <span className="text-xs font-bold text-purple-400">{c.name[0]}</span>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-200">{c.name}</p>
                      <p className="text-xs text-gray-500">{c.role} · {c.email || 'No email'}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <SectionHeader title={`Recent Activities (${account.activities?.length || 0})`} />
            {account.activities?.length === 0 ? (
              <p className="text-sm text-gray-500">No CRM activities on record.</p>
            ) : (
              <div className="space-y-2">
                {account.activities?.slice(0, 10).map((a) => (
                  <div key={a.activity_id} className="p-2 rounded bg-[#1e2535]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-gray-300 capitalize">{a.activity_type}</span>
                      <span className="text-xs text-gray-500">
                        {a.activity_date ? new Date(a.activity_date).toLocaleDateString() : 'Unknown date'}
                      </span>
                    </div>
                    {a.notes && <p className="text-xs text-gray-400 mt-1">{a.notes}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </Layout>
  )
}
