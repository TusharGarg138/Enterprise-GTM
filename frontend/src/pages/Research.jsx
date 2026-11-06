import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout } from '../components/Layout'
import { LoadingState } from '../components/ui'
import { createAccount, triggerResearch, getJobStatus } from '../services/api'
import { Search, Globe, Play, CheckCircle, XCircle } from 'lucide-react'

export default function Research() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ company_name: '', industry: '', website: '', employee_band: '', company_description: '' })
  const [creating, setCreating] = useState(false)
  const [researching, setResearching] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [createdAccount, setCreatedAccount] = useState(null)
  const [error, setError] = useState(null)

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.company_name.trim()) { setError('Company name is required.'); return }
    setCreating(true)
    setError(null)
    try {
      const res = await createAccount(form)
      const accountId = res?.data?.account_id
      setCreatedAccount({ id: accountId, name: form.company_name })

      // Auto-trigger research if website provided
      if (form.website && accountId) {
        setResearching(true)
        const jobRes = await triggerResearch(accountId)
        const jid = jobRes?.data?.job_id
        setJobId(jid)
        setJobStatus({ status: 'queued' })
        pollJob(jid, accountId)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  const pollJob = async (jid, accountId) => {
    const poll = async () => {
      try {
        const res = await getJobStatus(jid)
        const status = res?.data
        setJobStatus(status)
        if (status?.status === 'complete') {
          setResearching(false)
          setTimeout(() => navigate(`/accounts/${accountId}`), 1500)
        } else if (status?.status === 'failed') {
          setResearching(false)
          setError(`Research failed: ${status.error_message || 'Unknown error'}`)
        } else {
          setTimeout(poll, 3000)
        }
      } catch {
        setTimeout(poll, 3000)
      }
    }
    setTimeout(poll, 2000)
  }

  const EMPLOYEE_BANDS = ['1-10', '10-50', '50-200', '200-500', '500-1000', '1000-5000', '5000+']
  const INDUSTRIES = ['Technology', 'Finance', 'Healthcare', 'Retail', 'Manufacturing', 'Professional Services', 'Education', 'Media', 'Energy', 'Logistics', 'Other']

  return (
    <Layout title="Research" subtitle="Research a company using public information">
      <div className="max-w-2xl">
        {!createdAccount ? (
          <div className="card">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-blue-900/30 border border-blue-800/30 flex items-center justify-center">
                <Search className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-gray-100">New Company Research</h2>
                <p className="text-sm text-gray-400">Enter a company's details to begin AI-powered research.</p>
              </div>
            </div>

            {error && (
              <div className="mb-4 p-3 rounded-lg bg-red-900/20 border border-red-800/30 text-sm text-red-300">
                {error}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Company Name <span className="text-red-400">*</span></label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="e.g. Acme Corporation"
                  value={form.company_name}
                  onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))}
                  required
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Company Website</label>
                <div className="relative">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type="url"
                    className="input-field pl-10"
                    placeholder="https://company.com"
                    value={form.website}
                    onChange={e => setForm(f => ({ ...f, website: e.target.value }))}
                  />
                </div>
                <p className="text-xs text-gray-600 mt-1">
                  Providing a website enables automatic AI research of publicly available information.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">Industry</label>
                  <select
                    className="input-field"
                    value={form.industry}
                    onChange={e => setForm(f => ({ ...f, industry: e.target.value }))}
                  >
                    <option value="">Select industry</option>
                    {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">Company Size</label>
                  <select
                    className="input-field"
                    value={form.employee_band}
                    onChange={e => setForm(f => ({ ...f, employee_band: e.target.value }))}
                  >
                    <option value="">Select size</option>
                    {EMPLOYEE_BANDS.map(b => <option key={b} value={b}>{b} employees</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Brief Description (optional)</label>
                <textarea
                  className="input-field resize-none h-20"
                  placeholder="What does this company do?"
                  value={form.company_description}
                  onChange={e => setForm(f => ({ ...f, company_description: e.target.value }))}
                />
              </div>

              <button
                type="submit"
                className="btn-primary w-full flex items-center justify-center gap-2"
                disabled={creating}
              >
                <Play className="w-4 h-4" />
                {creating ? 'Creating account...' : 'Create Account & Start Research'}
              </button>
            </form>
          </div>
        ) : (
          <div className="card">
            <div className="flex items-center gap-3 mb-6">
              {jobStatus?.status === 'complete' ? (
                <CheckCircle className="w-8 h-8 text-green-400" />
              ) : jobStatus?.status === 'failed' ? (
                <XCircle className="w-8 h-8 text-red-400" />
              ) : (
                <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
              )}
              <div>
                <h2 className="text-base font-semibold text-gray-100">
                  {jobStatus?.status === 'complete' ? 'Research Complete!' :
                   jobStatus?.status === 'failed' ? 'Research Failed' :
                   'Research in Progress'}
                </h2>
                <p className="text-sm text-gray-400">{createdAccount.name}</p>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 rounded bg-[#1e2535]">
                <CheckCircle className="w-4 h-4 text-green-400 shrink-0" />
                <span className="text-sm text-gray-300">Account created successfully</span>
              </div>
              {form.website && (
                <div className="flex items-center gap-3 p-3 rounded bg-[#1e2535]">
                  {jobStatus?.status === 'complete' ? (
                    <CheckCircle className="w-4 h-4 text-green-400 shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-blue-400 border-t-transparent animate-spin shrink-0" />
                  )}
                  <span className="text-sm text-gray-300">
                    Multi-agent research: {jobStatus?.status || 'starting...'}
                  </span>
                </div>
              )}
            </div>

            {error && (
              <div className="mt-4 p-3 rounded-lg bg-red-900/20 border border-red-800/30 text-sm text-red-300">
                {error}
              </div>
            )}

            <div className="mt-6 flex gap-3">
              <button
                className="btn-primary text-sm"
                onClick={() => navigate(`/accounts/${createdAccount.id}`)}
              >
                View Account
              </button>
              <button className="btn-secondary text-sm" onClick={() => {
                setCreatedAccount(null)
                setJobId(null)
                setJobStatus(null)
                setError(null)
                setForm({ company_name: '', industry: '', website: '', employee_band: '', company_description: '' })
              }}>
                Research Another
              </button>
            </div>
          </div>
        )}

        {/* Instructions */}
        <div className="mt-6 card">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">How Research Works</h3>
          <div className="space-y-3">
            {[
              ['1. Data Collection', 'Public company website content is extracted and stored locally.'],
              ['2. AI Analysis', 'Four specialized agents analyze company info, opportunities, risks, and strategy.'],
              ['3. Deterministic Scoring', 'Account score is calculated using Python logic — not AI-invented numbers.'],
              ['4. Grounded Report', 'All findings reference actual sources. AI never invents company information.'],
            ].map(([title, desc]) => (
              <div key={title} className="flex gap-3">
                <span className="text-blue-400 text-sm font-medium shrink-0">{title}</span>
                <span className="text-sm text-gray-400">{desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Layout>
  )
}
