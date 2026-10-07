import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, type ActivityEvent, type CashAccount, type Ticket } from './api'

const AGENTS = ['Boss', 'Inventory', 'Accounting', 'Facilities', 'Customer Service']

const ticketLabels: Record<number, string> = {
  101: 'Fulfillment',
  102: 'Facilities',
  103: 'Pricing',
}

function money(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(new Date(value))
}

function approvalFor(ticket: Ticket) {
  if (ticket.status !== 'in_progress') return null
  if (ticket.id === 101) {
    return { action: 'purchase' as const, reference_type: 'invoice' as const, reference_id: 501, amount: 840, label: 'Approve reprint invoice', detail: 'Invoice 501 · Bulldog Print Co' }
  }
  if (ticket.id === 102) {
    return { action: 'payment' as const, reference_type: 'lease' as const, reference_id: 1, amount: 2400, label: 'Approve rent payment', detail: 'Lease 1 · Chapel Street shop' }
  }
  return null
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [cash, setCash] = useState<CashAccount | null>(null)
  const [activity, setActivity] = useState<ActivityEvent[]>([])
  const [selectedId, setSelectedId] = useState(101)
  const [isRunning, setIsRunning] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [approvedBy, setApprovedBy] = useState('Operations desk')
  const [result, setResult] = useState('')
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    const [nextTickets, nextCash, nextActivity] = await Promise.all([api.tickets(), api.cash(), api.activity()])
    setTickets(nextTickets)
    setCash(nextCash)
    setActivity(nextActivity)
  }, [])

  useEffect(() => {
    refresh().catch((reason: Error) => setError(reason.message))
  }, [refresh])

  useEffect(() => {
    if (!isRunning) return undefined
    const interval = window.setInterval(() => refresh().catch(() => undefined), 1200)
    return () => window.clearInterval(interval)
  }, [isRunning, refresh])

  const selected = tickets.find((ticket) => ticket.id === selectedId) ?? tickets[0]
  const sessionActivity = useMemo(() => {
    const latestReset = [...activity]
      .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
      .filter((event) => event.agent === 'System' && event.action === 'reset')
      .at(-1)
    return latestReset
      ? activity.filter((event) => event.timestamp >= latestReset.timestamp)
      : activity
  }, [activity])
  const currentTicketActivity = useMemo(() => {
    if (!selected) return []
    const eventsSinceReset = [...sessionActivity].sort((a, b) => a.timestamp.localeCompare(b.timestamp))
    const marker = `analyze ticket ${selected.id}`
    const latestRunStart = eventsSinceReset
      .filter((event) => event.agent === 'Boss' && event.action === 'analysis' && event.detail.toLowerCase().includes(marker))
      .at(-1)
    return latestRunStart
      ? eventsSinceReset.filter((event) => event.timestamp >= latestRunStart.timestamp)
      : []
  }, [sessionActivity, selected])
  const agentSummaries = useMemo(() => AGENTS.map((agent) => ({
    agent,
    event: [...currentTicketActivity].reverse().find((item) => item.agent === agent && item.action === 'result'),
  })), [currentTicketActivity])

  async function runSelectedTicket() {
    if (!selected) return
    setError('')
    setResult('')
    setIsRunning(true)
    try {
      const response = await api.runTicket(selected.id)
      setResult(response.result)
      await refresh()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to run this ticket.')
    } finally {
      setIsRunning(false)
    }
  }

  async function approve() {
    if (!selected) return
    const approval = approvalFor(selected)
    if (!approval) return
    setError('')
    setIsApproving(true)
    try {
      await api.approve({ ...approval, account: 'checking', approved_by: approvedBy })
      await refresh()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to record approval.')
    } finally {
      setIsApproving(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Campus Customs · Operations Desk</p>
          <h1>Agent dashboard</h1>
          <p className="subhead">Review live tickets, monitor the team, and keep approvals with a human operator.</p>
        </div>
        <section className="cash-card" aria-label="Checking balance">
          <span>Checking balance</span>
          <strong>{cash ? money(cash.balance) : '—'}</strong>
          <small>{cash ? `As of ${cash.date}` : 'Loading live data'}</small>
        </section>
      </header>

      {error && <div className="notice error">{error}</div>}
      <section className="ticket-grid" aria-label="Open operations tickets">
        {tickets.map((ticket) => (
          <button
            className={`ticket-card ${ticket.id === selected?.id ? 'selected' : ''}`}
            key={ticket.id}
            onClick={() => { setSelectedId(ticket.id); setResult(''); setError('') }}
          >
            <div className="ticket-card-top"><span>Ticket {ticket.id}</span><StatusBadge status={ticket.status} /></div>
            <strong>{ticket.subject}</strong>
            <p>{ticket.requester}</p>
            <small>{ticketLabels[ticket.id]} · {ticket.notes}</small>
          </button>
        ))}
      </section>

      {selected && <section className="workspace">
        <article className="panel primary-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Selected workflow</p>
              <h2>Ticket {selected.id}: {selected.subject}</h2>
            </div>
            <StatusBadge status={selected.status} />
          </div>
          <div className="facts">
            <div><span>Requester</span><strong>{selected.requester}</strong></div>
            <div><span>Request</span><strong>{selected.qty ?? '—'} × {selected.sku ?? selected.subject} {selected.size ? `· ${selected.size}` : ''}</strong></div>
            <div><span>Reference</span><strong>{selected.invoice_id ? `Invoice ${selected.invoice_id}` : selected.lease_id ? `Lease ${selected.lease_id}` : 'No linked record'}</strong></div>
          </div>
          <p className="ticket-note">{selected.notes}</p>
          <button className="run-button" onClick={runSelectedTicket} disabled={isRunning || selected.status === 'resolved'}>
            {isRunning ? 'Agent team is working…' : selected.status === 'resolved' ? 'Workflow resolved' : 'Run agent team'}
          </button>
          {result && <div className="result"><h3>Latest Boss recommendation</h3><pre>{result}</pre></div>}
        </article>

        <aside className="panel activity-panel">
          <div className="panel-heading"><div><p className="eyebrow">Live trace</p><h2>Agent activity</h2></div><span className={isRunning ? 'live-dot active' : 'live-dot'}>{isRunning ? 'Refreshing' : 'Recent'}</span></div>
          <div className="activity-list">
            {sessionActivity.slice(0, 14).map((event, index) => <ActivityRow key={`${event.timestamp}-${index}`} event={event} />)}
            {!sessionActivity.length && <p className="empty">No activity in this session yet. Select a ticket and run the team.</p>}
          </div>
        </aside>
      </section>}

      {selected && <section className="lower-grid">
        <article className="panel contributions">
          <div className="panel-heading"><div><p className="eyebrow">Selected-ticket view</p><h2>Who contributed</h2></div></div>
          <div className="contribution-grid">
            {agentSummaries.map(({ agent, event }) => (
              <section className={`contribution agent-${agent.toLowerCase().replaceAll(' ', '-')}`} key={agent}>
                <span className="agent-dot" />
                <h3>{agent}</h3>
                <p>{event ? event.detail : `No current-run result for Ticket ${selected.id} yet.`}</p>
              </section>
            ))}
          </div>
        </article>

        <aside className="panel approval-panel">
          <p className="eyebrow">Human control</p>
          <h2>Approval desk</h2>
          {approvalFor(selected) ? <>
            <p className="approval-copy">{approvalFor(selected)?.detail}. The agent can recommend this action, but only this control can record it.</p>
            <div className="approval-amount">{money(approvalFor(selected)!.amount)}</div>
            <label>Approved by<input value={approvedBy} onChange={(event) => setApprovedBy(event.target.value)} /></label>
            <button className="approve-button" onClick={approve} disabled={isApproving || !approvedBy.trim()}>
              {isApproving ? 'Recording approval…' : approvalFor(selected)!.label}
            </button>
            <small>The backend rejects any approval that would make checking negative.</small>
          </> : <p className="empty">{selected.status === 'open' ? 'Run the agent team before a human approval can be considered.' : 'No money action is required for this ticket. Ticket 103 resolves from the completed recommendation; resolved tickets need no further approval.'}</p>}
        </aside>
      </section>}
    </main>
  )
}

function StatusBadge({ status }: { status: Ticket['status'] }) {
  return <span className={`status status-${status.replace('_', '-')}`}>{status.replace('_', ' ')}</span>
}

function ActivityRow({ event }: { event: ActivityEvent }) {
  return <div className={`activity-row agent-${event.agent.toLowerCase().replaceAll(' ', '-')}`}>
    <span className="agent-dot" />
    <div><strong>{event.agent}</strong><span>{event.action.replace('_', ' ')}</span><p>{event.mcp_tool ? `Used ${event.mcp_tool}` : event.delegation_to ? `Delegated to ${event.delegation_to}` : event.detail}</p></div>
    <time>{formatTime(event.timestamp)}</time>
  </div>
}
