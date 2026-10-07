# Campus Customs agent dashboard

## Layout

The dashboard begins with the live checking balance and three ticket cards, so an operator can assess the queue before opening a workflow. Selecting a ticket makes its facts, status, run control, agent trace, contribution summaries, and any required human approval visible in one desk-like workspace.

The main workspace pairs the selected ticket with a scrolling activity feed. The lower row places per-agent contribution cards beside the human approval desk. This keeps recommendations and financial control close together without treating an agent recommendation as an executed action.

## Visual system

The interface uses a white and very light blush background, white cards, restrained pink action accents, and dark plum text for comfortable scanning. Soft borders and shallow shadows separate information without making the screen decorative. Status badges use pink for open, amber for in progress, and green for resolved.

Each agent is identified with a consistent colored dot: Boss is pink, Inventory blue, Accounting gold, Facilities green, and Customer Service violet. The same colors appear in the activity feed and contribution cards, letting a human see the shape of a delegation quickly without turning the UI into a cartoon.

## Operations behavior

The ticket cards, balance, activity feed, agent recommendation, and approval actions all call the FastAPI backend. During a run, the activity feed refreshes every 1.2 seconds. The approval desk only appears for ticket 101’s invoice 501 purchase or ticket 102’s lease 1 rent payment; it calls `/approvals`, then refreshes balance and ticket status. Ticket 103 needs no money approval.

Resolved tickets stay visibly resolved and their run controls are disabled. The design keeps the cash balance prominent and labels approval as a human-control step, making it useful as an operations desk rather than a chat interface.
