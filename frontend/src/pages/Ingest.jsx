import { useState } from 'react'
import { Layout } from '../components/Layout'
import { ingestCSV } from '../services/api'
import { Upload, FileSpreadsheet, CheckCircle, AlertTriangle } from 'lucide-react'

export default function Ingest() {
  const [csvType, setCsvType] = useState('accounts')
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    setError(null)
    setResult(null)

    try {
      const res = await ingestCSV(file, csvType)
      setResult(res?.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <Layout title="Data Ingestion" subtitle="Import Synthetic CRM Data into PostgreSQL">
      <div className="max-w-2xl">
        <div className="card mb-6">
          <h2 className="text-base font-semibold text-gray-100 mb-1">Upload CRM CSV Dataset</h2>
          <p className="text-xs text-gray-400 mb-4">
            Upload CSV files for accounts, contacts, activities, or opportunities. The validator checks column schema, foreign keys, and date ranges.
          </p>

          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Dataset Entity Type</label>
              <select
                className="input-field"
                value={csvType}
                onChange={e => setCsvType(e.target.value)}
              >
                <option value="accounts">Accounts (accounts.csv)</option>
                <option value="contacts">Contacts (contacts.csv)</option>
                <option value="activities">Activities (activities.csv)</option>
                <option value="opportunities">Opportunities (opportunities.csv)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Select CSV File</label>
              <input
                type="file"
                accept=".csv"
                onChange={e => setFile(e.target.files[0])}
                className="block w-full text-xs text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-500 cursor-pointer"
              />
            </div>

            <button
              type="submit"
              className="btn-primary w-full flex items-center justify-center gap-2"
              disabled={!file || uploading}
            >
              <Upload className="w-4 h-4" />
              {uploading ? 'Processing & Validating...' : 'Upload & Validate CSV'}
            </button>
          </form>

          {error && (
            <div className="mt-4 p-3 rounded-lg bg-red-900/20 border border-red-800/30 text-sm text-red-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {result && (
            <div className="mt-4 p-4 rounded-lg bg-green-900/20 border border-green-800/30">
              <div className="flex items-center gap-2 text-green-400 font-semibold text-sm mb-2">
                <CheckCircle className="w-4 h-4" />
                <span>Upload Processed Successfully</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-[#161b27] p-2 rounded">
                  <p className="text-gray-500">Processed</p>
                  <p className="text-gray-200 font-bold">{result.rows_processed}</p>
                </div>
                <div className="bg-[#161b27] p-2 rounded">
                  <p className="text-gray-500">Inserted</p>
                  <p className="text-green-400 font-bold">{result.rows_inserted}</p>
                </div>
                <div className="bg-[#161b27] p-2 rounded">
                  <p className="text-gray-500">Skipped</p>
                  <p className="text-yellow-400 font-bold">{result.rows_skipped}</p>
                </div>
              </div>
              {result.errors && result.errors.length > 0 && (
                <div className="mt-3 text-xs text-red-400">
                  <p className="font-semibold mb-1">Errors/Warnings:</p>
                  <ul className="list-disc pl-4 space-y-0.5">
                    {result.errors.slice(0, 5).map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="text-sm font-semibold text-gray-200 mb-2">Sample Synthetic Data Files</h3>
          <p className="text-xs text-gray-400 mb-3">
            Pre-generated realistic CRM CSV datasets are located under <code className="text-blue-400 bg-[#1e2535] px-1 py-0.5 rounded">data/sample_crm/</code>.
          </p>
          <div className="space-y-1.5 text-xs text-gray-300">
            <p>• <strong>accounts.csv</strong>: 20 accounts across multiple industries</p>
            <p>• <strong>contacts.csv</strong>: Executives and decision makers linked by company name</p>
            <p>• <strong>activities.csv</strong>: Calls, meetings, emails across engagement levels</p>
            <p>• <strong>opportunities.csv</strong>: Deals across all qualification pipeline stages</p>
          </div>
        </div>
      </div>
    </Layout>
  )
}
