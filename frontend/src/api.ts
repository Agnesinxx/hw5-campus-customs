export const API_URL = 'http://localhost:8000'

export type TicketStatus = 'open' | 'in_progress' | 'resolved'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: TicketStatus
  notes: string | null
  created_at: string
  resolution_state: 'open' | 'resolved'
}

export interface CashAccount {
  name: string
  balance: number
  date: string
}

export interface ActivityEvent {
  timestamp: string
  agent: string
  action: string
  detail: string
  delegation_to: string | null
  mcp_tool: string | null
}

export interface RunTicketResponse {
  ticket_id: number
  status: TicketStatus
  result: string
}

export interface ApprovalRequest {
  action: 'payment' | 'purchase'
  reference_type: 'lease' | 'invoice'
  reference_id: number
  amount: number
  account: string
  approved_by: string
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  tickets: () => request<Ticket[]>('/tickets'),
  cash: () => request<CashAccount>('/cash'),
  activity: () => request<ActivityEvent[]>('/activity?limit=100'),
  runTicket: (ticketId: number) => request<RunTicketResponse>(`/tickets/${ticketId}/run`, { method: 'POST' }),
  approve: (payload: ApprovalRequest) => request<{ approved: boolean; new_balance: number }>('/approvals', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
}
