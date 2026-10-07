# Campus Customs Multi-Agent Operations

Campus Customs is a small operations desk built for Homework 5. Five PydanticAI agents—Boss, Inventory, Accounting, Facilities, and Customer Service—use the local FastMCP server for shop facts. The FastAPI backend keeps all cash-changing actions behind human approval, and the React dashboard displays ticket state, activity, and balance.

## Requirements

- Python 3.11+ and Node.js 20+
- A Portkey API key for agent runs

From the project root (`hw5`), create the local key file and install Python dependencies:

```bash
cp .env.example .env
# Edit .env and set PORTKEY_API_KEY.
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.env` is intentionally ignored by Git. Do not commit an API key.

## Reset the working data

`data/campus_customs.db` is the untouched baseline. `data/campus_customs_new.db` is the working database used by the MCP server and backend. To reset the working database manually from the project root:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

The backend also provides `POST /reset`, which restores the same working database and records the reset in the audit trail.

## Run the local services

Run each command in its own terminal, from the indicated directory.

### MCP server (optional for direct inspection)

From `hw5`:

```bash
python mcp_server/server.py
```

The included `.mcp.json` config points Codex to `mcp_server/server.py`. The backend starts an MCP stdio connection itself during agent runs, so a separate MCP terminal is not required for normal dashboard use.

### FastAPI backend

From `hw5/backend`:

```bash
uvicorn main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. It allows the Vite dashboard origin on port 5173.

### React dashboard

From `hw5/frontend`:

```bash
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`).

## Submission evidence

- `output/desk_tickets.html` — Expected/Actual ticket plans, cash reconciliation, and reflection
- `output/resolved_tickets.json` — final outcomes, agent contributions, tool use, and approvals
- `output/resolved_board.html` — resolved dashboard evidence, including a selected resolved screenshot for each ticket
- `output/audit_trail.json` — append-only event record
- `output/harness.md` — database, MCP-tool, agent, safety, and route reference

The preserved completed working state has tickets 101–103 resolved, invoice 501 paid, and a `$160.00` checking balance.
