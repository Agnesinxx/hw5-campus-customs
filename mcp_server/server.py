"""FastMCP tools for the Campus Customs operations database."""

import sqlite3
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"
mcp = FastMCP("Campus Customs Operations")


def _query_one(query: str, parameters: tuple[Any, ...]) -> dict[str, Any] | None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(query, parameters).fetchone()
        return dict(row) if row is not None else None


def _query_all(query: str, parameters: tuple[Any, ...]) -> list[dict[str, Any]]:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]


@mcp.tool()
def check_inventory(sku: str, size: str) -> dict[str, Any]:
    """Look up inventory quantity and location for one SKU and size."""
    row = _query_one("SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?", (sku, size))
    return {"found": False, "sku": sku, "size": size} if row is None else {"found": True, **row}


@mcp.tool()
def get_lease(lease_id: int) -> dict[str, Any]:
    """Look up a lease by ID, including rent and the next due date."""
    row = _query_one("SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?", (lease_id,))
    return {"found": False, "lease_id": lease_id} if row is None else {"found": True, **row}


@mcp.tool()
def get_invoice(invoice_id: int) -> dict[str, Any]:
    """Look up an invoice by ID and include its related vendor details."""
    row = _query_one(
        """SELECT invoices.id, invoices.vendor_id, invoices.amount, invoices.due_date,
        invoices.status, invoices.description, vendors.name AS vendor_name,
        vendors.specialty AS vendor_specialty, vendors.lead_days AS vendor_lead_days
        FROM invoices JOIN vendors ON vendors.id = invoices.vendor_id
        WHERE invoices.id = ?""",
        (invoice_id,),
    )
    return {"found": False, "invoice_id": invoice_id} if row is None else {"found": True, **row}


@mcp.tool()
def get_ticket(ticket_id: int) -> dict[str, Any]:
    """Look up an operations ticket by ID."""
    row = _query_one(
        """SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id,
        status, notes, created_at FROM tickets WHERE id = ?""",
        (ticket_id,),
    )
    return {"found": False, "ticket_id": ticket_id} if row is None else {"found": True, **row}


@mcp.tool()
def get_pricing(sku: str) -> dict[str, Any]:
    """Look up the unit cost and list price for one SKU."""
    row = _query_one("SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,))
    return {"found": False, "sku": sku} if row is None else {"found": True, **row}


@mcp.tool()
def get_cash_account(account: str) -> dict[str, Any]:
    """Look up the current balance and date for a cash account."""
    row = _query_one("SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,))
    return {"found": False, "account": account} if row is None else {"found": True, **row}


@mcp.tool()
def get_payments_for_reference(ref_id: int) -> dict[str, Any]:
    """List recorded payments whose reference ID matches the supplied record ID."""
    rows = _query_all(
        """SELECT id, kind, ref_id, amount, account, paid_at, approved_by
        FROM payments WHERE ref_id = ? ORDER BY paid_at, id""",
        (ref_id,),
    )
    return {"ref_id": ref_id, "count": len(rows), "payments": rows}


if __name__ == "__main__":
    mcp.run()
