import { useState, useEffect } from 'react'
import { Layout } from '../components/Layout'
import { LoadingState, ErrorState } from '../components/ui'
import { getAccounts, sendChatMessage } from '../services/api'
import { MessageSquare, Send, Sparkles, Building2, BookOpen } from 'lucide-react'

export default function Chat() {
  const [accounts, setAccounts] = useState([])
  const [selectedAccountId, setSelectedAccountId] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I am your Enterprise GTM Sales Assistant. Select an account to ask grounded questions based on its ingested website and CRM data.',
      sources: []
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getAccounts({ page_size: 100 })
      .then(res => {
        const items = res?.data?.items || []
        setAccounts(items)
        if (items.length > 0) {
          setSelectedAccountId(items[0].account_id)
        }
      })
      .catch(() => {})
  }, [])

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim() || !selectedAccountId || loading) return

    const userText = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userText }])
    setLoading(true)

    try {
      const res = await sendChatMessage({
        account_id: selectedAccountId,
        question: userText
      })

      const data = res?.data
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data?.answer || 'No response returned.',
          sources: data?.sources || []
        }
      ])
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${err.message || 'Failed to get answer.'}`,
          sources: []
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  const selectedAccount = accounts.find(a => a.account_id === selectedAccountId)

  return (
    <Layout title="Ask Intelligence (RAG Chat)" subtitle="Grounded Q&A over ingested documents and CRM records">
      <div className="max-w-4xl mx-auto h-[calc(100vh-140px)] flex flex-col card p-0 overflow-hidden">
        {/* Account selector banner */}
        <div className="p-4 bg-[#1e2535] border-b border-[#2a3348] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="w-5 h-5 text-blue-400" />
            <span className="text-sm font-medium text-gray-300">Target Account:</span>
            <select
              className="input-field py-1 text-sm bg-[#161b27]"
              value={selectedAccountId}
              onChange={e => setSelectedAccountId(e.target.value)}
            >
              {accounts.map(a => (
                <option key={a.account_id} value={a.account_id}>
                  {a.company_name} ({a.industry || 'General'})
                </option>
              ))}
            </select>
          </div>
          <span className="text-xs text-gray-500 hidden sm:inline">Zero hallucination · Grounded in vectors</span>
        </div>

        {/* Message history */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-xl p-3.5 text-sm ${
                  m.role === 'user'
                    ? 'bg-blue-600 text-white rounded-br-none'
                    : 'bg-[#1e2535] border border-[#2a3348] text-gray-200 rounded-bl-none'
                }`}
              >
                <p className="whitespace-pre-wrap">{m.content}</p>

                {/* Sources grounding box */}
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-[#2a3348]">
                    <div className="flex items-center gap-1.5 text-xs text-blue-400 font-semibold mb-1">
                      <BookOpen className="w-3.5 h-3.5" />
                      Grounded Sources ({m.sources.length})
                    </div>
                    <div className="space-y-1.5">
                      {m.sources.map((s, sidx) => (
                        <div key={sidx} className="text-[11px] bg-[#161b27] p-1.5 rounded border border-[#2a3348]">
                          <div className="flex justify-between text-gray-400 font-medium">
                            <span className="truncate max-w-[200px]">{s.source_title || s.source_url || 'Website Document'}</span>
                            <span className="text-blue-400 font-mono">{(s.relevance_score * 100).toFixed(0)}% match</span>
                          </div>
                          <p className="text-gray-500 line-clamp-2 mt-0.5">{s.chunk_text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-2 text-xs text-gray-400 p-2">
              <Sparkles className="w-4 h-4 text-blue-400 animate-spin" />
              Retrieving context & generating grounded answer...
            </div>
          )}
        </div>

        {/* Prompt input */}
        <form onSubmit={handleSend} className="p-3 bg-[#161b27] border-t border-[#2a3348] flex gap-2">
          <input
            type="text"
            className="input-field flex-1"
            placeholder={selectedAccount ? `Ask a question about ${selectedAccount.company_name}...` : 'Ask a question...'}
            value={input}
            onChange={e => setInput(e.target.value)}
            disabled={loading || !selectedAccountId}
          />
          <button
            type="submit"
            className="btn-primary px-4 py-2 flex items-center justify-center gap-1"
            disabled={loading || !input.trim() || !selectedAccountId}
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </Layout>
  )
}
