import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: add request ID for tracing
api.interceptors.request.use((config) => {
  config.headers['X-Request-ID'] = Math.random().toString(36).substring(2, 10)
  return config
})

// Response interceptor: unwrap data, handle errors gracefully
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.message ||
      error.response?.data?.detail ||
      error.message ||
      'An unexpected error occurred.'
    return Promise.reject(new Error(message))
  }
)

// ─── Health ──────────────────────────────────────────────────────────────────
export const getHealth = () => api.get('/health')

// ─── Accounts ────────────────────────────────────────────────────────────────
export const getAccounts = (params = {}) => api.get('/accounts', { params })
export const getAccount = (accountId) => api.get(`/accounts/${accountId}`)
export const createAccount = (data) => api.post('/accounts', data)
export const updateAccount = (accountId, data) => api.patch(`/accounts/${accountId}`, data)
export const deleteAccount = (accountId) => api.delete(`/accounts/${accountId}`)

// ─── Research ────────────────────────────────────────────────────────────────
export const triggerResearch = (accountId, params = {}) =>
  api.post(`/accounts/${accountId}/research`, null, { params })
export const getJobStatus = (jobId) => api.get(`/research/jobs/${jobId}`)
export const getAccountReports = (accountId) => api.get(`/accounts/${accountId}/reports`)

// ─── Reports ─────────────────────────────────────────────────────────────────
export const getReport = (reportId) => api.get(`/reports/${reportId}`)
export const getReports = (limit = 50) => api.get('/reports', { params: { limit } })

// ─── Opportunities ───────────────────────────────────────────────────────────
export const getOpportunities = (params = {}) => api.get('/opportunities', { params })
export const getOpportunity = (opportunityId) => api.get(`/opportunities/${opportunityId}`)

// ─── Ingestion ────────────────────────────────────────────────────────────────
export const ingestWebsite = (data) => api.post('/ingestion/website', data)
export const ingestCSV = (file, csvType) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('csv_type', csvType)
  return api.post('/ingestion/csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ─── Chat ─────────────────────────────────────────────────────────────────────
export const sendChatMessage = (data) => api.post('/chat', data)

export default api
