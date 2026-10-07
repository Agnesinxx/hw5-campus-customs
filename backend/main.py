"""FastAPI routes for the Campus Customs agent workflow.

The agent team remains MCP-only. This module reads the working database for dashboard
routes and is the single, human-approved boundary permitted to write payments.
"""

import json
import shutil
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:  # Supports both `uvicorn backend.main:app` and `cd backend && uvicorn main:app`.
    from .audit import AUDIT_TRAIL_PATH, append_audit_event
    from .team import CampusCustomsTeam
except ImportError:  # pragma: no cover - exercised by the assignment's launch command.
    from audit import AUDIT_TRAIL_PATH, append_audit_event
    from team import CampusCustomsTeam


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "campus_customs_new.db"
ORIGINAL_DATABASE_PATH = DATA_DIR / "campus_customs.db"

app = FastAPI(title="Campus Customs Operations API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApprovalRequest(BaseModel):
    """A human-confirmed payment or invoice-backed purchase."""

    action: Literal["payment", "purchase"]
    reference_type: Literal["lease", "invoice"]
    reference_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    account: str = Field(default="checking", min_length=1, max_length=100)
    approved_by: str = Field(min_length=1, max_length=100)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _row_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


@app.get("/tickets")
def list_tickets() -> list[dict]:
    """Return the three tracked tickets and their open/resolved state."""
    with _connection() as connection:
        rows = connection.execute(
            """SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id,
            status, notes, created_at,
            CASE WHEN status = 'resolved' THEN 'resolved' ELSE 'open' END AS resolution_state
            FROM tickets WHERE id IN (101, 102, 103) ORDER BY id"""
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int) -> dict:
    """Run the existing Boss-led PydanticAI team for one existing ticket."""
    with _connection() as connection:
        ticket = connection.execute(
            "SELECT id, type, invoice_id, lease_id, status FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} was not found.")

    result = await CampusCustomsTeam().run_ticket(ticket_id)
    status = ticket["status"]
    if status != "resolved":
        if ticket["id"] == 103 and ticket["type"] == "price_override" and not ticket["invoice_id"]:
            # Ticket 103 is a no-cash recommendation: completed agent analysis closes it.
            status = "resolved"
        elif ticket["id"] == 101 and ticket["invoice_id"] == 501:
            # Ticket 101 depends on its actual linked reprint invoice, not a generic run outcome.
            with _connection() as connection:
                invoice = connection.execute("SELECT status FROM invoices WHERE id = ?", (ticket["invoice_id"],)).fetchone()
            status = "resolved" if invoice and invoice["status"] == "paid" else "in_progress"
        else:
            # Ticket 102 remains in progress until its lease payment is approved below.
            status = "in_progress"

        if status != ticket["status"]:
            previous_status = ticket["status"]
            with _connection() as connection:
                connection.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
            append_audit_event(
                agent="System",
                action="ticket_status",
                detail=f"Ticket {ticket_id} moved from {previous_status} to {status} after agent analysis.",
            )
    return {"ticket_id": ticket_id, "status": status, "result": result}


@app.get("/activity")
def recent_activity(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    """Return the most recent persisted agent and approval activity first."""
    if not AUDIT_TRAIL_PATH.exists():
        return []
    try:
        events = json.loads(AUDIT_TRAIL_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=500, detail="The audit trail is not valid JSON.") from error
    return list(reversed(events[-limit:]))


@app.get("/cash")
def current_cash() -> dict:
    """Return the current checking balance and its as-of date."""
    with _connection() as connection:
        account = connection.execute(
            "SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'"
        ).fetchone()
    if account is None:
        raise HTTPException(status_code=404, detail="Checking account was not found.")
    return _row_dict(account)  # type: ignore[return-value]


@app.post("/reset")
def reset_working_data() -> dict:
    """Restore the working database from the unchanged original database."""
    if not ORIGINAL_DATABASE_PATH.exists():
        raise HTTPException(status_code=500, detail="Original database was not found.")
    shutil.copy2(ORIGINAL_DATABASE_PATH, DATABASE_PATH)
    append_audit_event(
        agent="System",
        action="reset",
        detail="Restored campus_customs_new.db from campus_customs.db.",
    )
    return {"reset": True, "database": "data/campus_customs_new.db"}


@app.post("/approvals")
def approve_money_action(request: ApprovalRequest) -> dict:
    """Execute the only permitted money write after an explicit human approval."""
    if request.action == "purchase" and request.reference_type != "invoice":
        raise HTTPException(status_code=400, detail="A purchase must reference an existing invoice.")

    with _connection() as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            account = connection.execute(
                "SELECT name, balance FROM cash_accounts WHERE name = ?", (request.account,)
            ).fetchone()
            if account is None:
                raise HTTPException(status_code=404, detail=f"Account '{request.account}' was not found.")
            if request.amount > account["balance"]:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Approval refused: ${request.amount:.2f} exceeds the "
                        f"${account['balance']:.2f} {request.account} balance."
                    ),
                )

            if request.reference_type == "invoice":
                reference = connection.execute(
                    "SELECT id, amount, status FROM invoices WHERE id = ?", (request.reference_id,)
                ).fetchone()
                if reference is None:
                    raise HTTPException(status_code=404, detail=f"Invoice {request.reference_id} was not found.")
                paid = connection.execute(
                    "SELECT COALESCE(SUM(amount), 0) AS paid FROM payments WHERE ref_id = ?",
                    (request.reference_id,),
                ).fetchone()["paid"]
                remaining = reference["amount"] - paid
                if request.amount > remaining:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Approval refused: invoice {request.reference_id} has only ${remaining:.2f} remaining.",
                    )
            else:
                reference = connection.execute(
                    "SELECT id, monthly_rent FROM leases WHERE id = ?", (request.reference_id,)
                ).fetchone()
                if reference is None:
                    raise HTTPException(status_code=404, detail=f"Lease {request.reference_id} was not found.")
                if request.amount > reference["monthly_rent"]:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Approval refused: lease {request.reference_id} monthly rent is "
                            f"${reference['monthly_rent']:.2f}."
                        ),
                    )

            paid_at = datetime.now(timezone.utc).isoformat()
            cursor = connection.execute(
                """INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (request.action, request.reference_id, request.amount, request.account, paid_at, request.approved_by),
            )
            new_balance = account["balance"] - request.amount
            connection.execute(
                "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
                (new_balance, date.today().isoformat(), request.account),
            )

            invoice_status: str | None = None
            if request.reference_type == "invoice":
                total_paid = connection.execute(
                    "SELECT COALESCE(SUM(amount), 0) AS paid FROM payments WHERE ref_id = ?",
                    (request.reference_id,),
                ).fetchone()["paid"]
                if total_paid >= reference["amount"]:
                    invoice_status = "paid"
                    connection.execute("UPDATE invoices SET status = ? WHERE id = ?", (invoice_status, request.reference_id))
                    connection.execute(
                        "UPDATE tickets SET status = 'resolved' WHERE invoice_id = ? AND status != 'resolved'",
                        (request.reference_id,),
                    )
            elif request.amount == reference["monthly_rent"]:
                connection.execute(
                    "UPDATE tickets SET status = 'resolved' WHERE lease_id = ? AND status != 'resolved'",
                    (request.reference_id,),
                )

            connection.commit()
        except HTTPException:
            connection.rollback()
            raise
        except sqlite3.Error as error:
            connection.rollback()
            raise HTTPException(status_code=500, detail="Unable to record the approved action.") from error

    append_audit_event(
        agent="Human Approval",
        action="approved_money_action",
        detail=(
            f"Approved {request.action} of ${request.amount:.2f} from {request.account} "
            f"for {request.reference_type} {request.reference_id}."
        ),
    )
    return {
        "approved": True,
        "payment_id": cursor.lastrowid,
        "new_balance": new_balance,
        "invoice_status": invoice_status,
    }
