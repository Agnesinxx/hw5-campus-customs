# Campus Customs MCP server

This FastMCP server exposes read-only operations data for Campus Customs agents. It reads from `../data/campus_customs_new.db` relative to this directory and does not modify the database.

- `check_inventory(sku, size)` reads `inventory` and returns the product, quantity, and location for tickets 101 and 103.
- `get_lease(lease_id)` reads `leases` and returns the space, landlord, monthly rent, next due date, and notes for ticket 102.
- `get_invoice(invoice_id)` reads `invoices` joined with `vendors` and returns invoice details plus related vendor information for ticket 101.
- `get_ticket(ticket_id)` reads `tickets` and returns the ticket facts and its SKU, lease, or invoice references.
- `get_pricing(sku)` reads `pricing` and returns the unit cost and list price needed to assess ticket 103.
- `get_cash_account(account)` reads `cash_accounts` and returns the balance and as-of date needed to assess ticket 102.
- `get_payments_for_reference(ref_id)` reads `payments` and returns recorded payments with that reference ID; ticket 102 uses lease ID 1.

The server intentionally has no write tools. Payment, discount, ordering, and outreach decisions remain human-approved operations.
