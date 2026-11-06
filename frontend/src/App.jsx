import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import AccountDetails from './pages/AccountDetails'
import Research from './pages/Research'
import Opportunities from './pages/Opportunities'
import Reports from './pages/Reports'
import Chat from './pages/Chat'
import Ingest from './pages/Ingest'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/accounts" element={<Accounts />} />
        <Route path="/accounts/:accountId" element={<AccountDetails />} />
        <Route path="/research" element={<Research />} />
        <Route path="/opportunities" element={<Opportunities />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/ingest" element={<Ingest />} />
      </Routes>
    </BrowserRouter>
  )
}
