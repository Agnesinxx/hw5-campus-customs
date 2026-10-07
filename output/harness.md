# Campus Customs database harness

## Tables

### `desk`

Fields: `date_today`, `notes`

The desk table records the operational date (`2026-08-31`) used to interpret current notices and due dates.

### `inventory`

Fields: `sku`, `name`, `size`, `qty`, `location`

The inventory table provides the available quantity and physical location for each product-size combination, including 0 size-S `CC-TEE-WHITE` units and 8 size-M `CC-HOOD-NAVY` units relevant to open tickets.

### `pricing`

Fields: `sku`, `unit_cost`, `list_price`

The pricing table gives the cost and list price for each SKU, allowing the agent to evaluate the `CC-HOOD-NAVY` bulk-discount request and product availability responses.

### `vendors`

Fields: `id`, `name`, `specialty`, `lead_days`

The vendors table identifies the supplier behind invoice 501 (`Bulldog Print Co`, an apparel reprint vendor with a 5-day lead time).

### `leases`

Fields: `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`

The leases table records lease 1 for the Chapel Street shop, including its $2,400 monthly rent and `2026-09-02` due date relevant to rent ticket 102.

### `cash_accounts`

Fields: `name`, `balance`, `date`

The cash_accounts table holds the live checking balance used by the approval guard; after the approved ticket-101 and ticket-102 transactions, it is $160 as of `2026-10-07`.

### `payments`

Fields: `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`

The payments table records approved invoice or lease-related obligations. It now contains the $840 invoice-501 purchase and the $2,400 lease-1 rent payment, both approved by Operations desk.

### `invoices`

Fields: `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`

The invoices table links invoice 501 for $840 to vendor 1 and identifies it as a rush reprint of `CC-TEE-WHITE` size S; the invoice is now marked paid after human approval.

### `tickets`

Fields: `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`

The tickets table is the operational work queue and contains the product, lease, and invoice references needed to connect each request to operational records; tickets 101, 102, and 103 are now resolved.

## Ticket reference data

### Ticket 101 — customer order

Ticket ID `101` is from Tauhid Zaman for one `CC-TEE-WHITE` (Classic Bulldog Tee) in size S; its note says, “Needs a tee in size S.” The relevant tables are `tickets` for the request, `inventory` for the size-S quantity (0 in Aisle B), `pricing` for the SKU’s $8 unit cost and $28 list price, and `invoices` because the ticket references the $840 rush reprint invoice `501`; `vendors` is also relevant through invoice 501’s `vendor_id` 1, Bulldog Print Co. The invoice is now paid and the ticket is resolved.

### Ticket 102 — rent notice

Ticket ID `102` is from Elm City Properties about rent due; its note says, “Email: shop rent due in 2 days.” The ticket references lease `1`, so `leases` is relevant for the Chapel Street shop’s $2,400 rent and `2026-09-02` next-due date; `cash_accounts` and `payments` verify that the human-approved $2,400 rent payment was affordable and recorded. The ticket is now resolved.

### Ticket 103 — price override

Ticket ID `103` is from Yale AI Club requesting a bulk discount for 20 `CC-HOOD-NAVY` (Basic Hoodie Big Yale) hoodies in size M. The relevant tables are `tickets` for the request, `inventory` for the 8 size-M units in Aisle A, and `pricing` for the $22 unit cost and $58 list price. Its completed recommendation required no money action, so the ticket is resolved.
## MCP tools

### `check_inventory(sku, size)`

Reads `inventory` and returns the matching SKU, product name, size, quantity, and location. It helps tickets `101` and `103`: ticket 101 needs size-S `CC-TEE-WHITE`, whose quantity is 0 in Aisle B, while ticket 103 requests size-M `CC-HOOD-NAVY`, whose quantity is 8 in Aisle A.

### `get_lease(lease_id)`

Reads `leases` and returns the lease’s space, landlord, monthly rent, next due date, and notes. It helps ticket `102` by looking up lease 1, the Chapel Street shop lease with $2,400 monthly rent due next on `2026-09-02`.

### `get_invoice(invoice_id)`

Reads `invoices` joined with `vendors` and returns the invoice fields plus the related vendor’s name, specialty, and lead time. It helps ticket `101` by looking up invoice 501, the $840 rush reprint for `CC-TEE-WHITE` size S from Bulldog Print Co., including its current paid status.

### `get_ticket(ticket_id)`

Reads `tickets` and returns the ticket’s request details and references. It gives every agent a database-grounded starting point for tickets `101`, `102`, and `103` instead of relying on ticket facts in a prompt.

### `get_pricing(sku)`

Reads `pricing` and returns unit cost and list price. It helps ticket `103` assess the requested hoodie discount using `CC-HOOD-NAVY`’s $22 unit cost and $58 list price.

### `get_cash_account(account)`

Reads `cash_accounts` and returns the current balance and as-of date. It helps ticket `102` assess whether the checking balance can cover the Chapel Street shop’s $2,400 rent without going negative before human approval.

### `get_payments_for_reference(ref_id)`

Reads `payments` and returns payment records for a reference ID. It verifies the approved invoice-501 purchase for ticket `101` and the approved lease-1 rent payment for ticket `102`.

## Agent team

### Boss

The Boss retrieves and triages an open ticket, then combines specialist findings into a recommendation without approving or carrying out operations.

### Inventory

Inventory checks product-size availability and related reprint information for the size-S tee in ticket `101` and the size-M hoodie quantity in ticket `103`.

### Accounting

Accounting reviews invoice, pricing, cash, and payment data for the rent notice in ticket `102` and the discount request in ticket `103`.

### Facilities

Facilities interprets the Chapel Street shop lease and its `2026-09-02` rent due date for ticket `102`.

### Customer Service

Customer Service creates truthful internal response recommendations for ticket `101` and ticket `103`, using stock and price facts confirmed through MCP.

## Safety limits

- The MCP server is read-only; a human must approve every payment, discount, order, or other database-changing action.
- Agents never contact real customers, vendors, landlords, or organizations; they produce internal recommendations only.
- Accounting must flag any action that would produce a negative cash balance; it cannot move money.
- Each run is bounded to 12 model requests, 20 tool calls, 8,000 total tokens, and a delegation depth of 3.
- `output/audit_trail.json` preserves agent actions, delegations, MCP tool calls, and results across runs.

## Backend routes

- `GET /tickets` — returns tickets 101, 102, and 103 with their stored status and computed open/resolved state.
- `POST /tickets/{ticket_id}/run` — runs the existing Boss-led agent team and moves an open ticket to `in_progress`; money-dependent tickets resolve only after approval.
- `GET /activity` — returns recent persisted agent, delegation, MCP-tool, and approval activity.
- `GET /cash` — returns the current checking balance and its as-of date.
- `POST /reset` — restores `campus_customs_new.db` from the unchanged original database.
- `POST /approvals` — records a human-approved invoice or lease payment only when it will not make the selected account negative; it updates the checking balance, payment record, and applicable invoice or rent ticket status.
