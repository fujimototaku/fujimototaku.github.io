# Revenue Machine v1

A revenue loop built around one principle: **a lead, proposal, or theoretical profit is worth $0 until the platform marks the work approved/paid.**

This repository intentionally separates acquisition channels by how automatable they really are.

## Lane A — CrowdWorks + GPT-6 Astra / ChatGPT Work

Use `ASTRA_WORK_CROWDWORKS.md` as the operating prompt in ChatGPT Work. The browser handles the logged-in UI; Astra evaluates jobs, writes tailored proposals, waits for escrow, completes the task, QA-checks it, delivers, and records only completed/paid work as revenue.

CrowdWorks officially permits AI use, but the client can set its own conditions. The prompt rejects jobs that prohibit AI, discloses AI/automation use when appropriate, never starts before escrow, and avoids mass spam.

## Lane B — Upwork official MCP

Upwork has an official MCP server that can let an AI agent find jobs, respond to invitations, submit proposals, review offers, and manage active contracts. See `UPWORK_MCP.md`.

## Lane C — ClawGig REST API (fully unattended proof lane)

This is the live code path implemented by `revenue_machine.py`.

Loop:
1. Pull open gigs from the official API.
2. Hard-filter risky / non-fulfillable tasks.
3. Use a reviewer model for opportunity scoring.
4. Use GPT-6 Astra only on high-value candidates.
5. Submit a truthful proposal.
6. Watch funded contracts.
7. Generate the finished deliverable.
8. Independent QA; one repair pass if needed.
9. Upload artifacts and deliver only when QA >= 90.
10. Count revenue only after contract status becomes `approved`.

### Commands

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python revenue_machine.py status
python revenue_machine.py scan
python revenue_machine.py cycle
python revenue_machine.py cycle --live-bid
python revenue_machine.py cycle --live-bid --live-delivery
```

### One-time setup for ClawGig

ClawGig requires a completed agent profile before proposals are accepted: operator claim, username, description, skills, languages, HTTPS avatar, HTTPS webhook, verified contact email, and a portfolio item. Do those once in the ClawGig dashboard, then store the API key only in environment variables / GitHub Actions secrets. **Never commit keys.**

### Economics gates

Defaults intentionally reject marginal work:
- minimum gig budget: 10 USDC
- at most 5 existing proposals
- AI accept score: 86/100
- estimated model cost <= 12% of gross budget
- bid defaults to <= 92% of listed budget
- risky external actions are hard-rejected

For small tasks, use the cheaper QA/triage model and reserve Astra for final proposals and execution. Astra is too expensive to spray across every listing.

## Scheduled execution

`.github/workflows/revenue-machine.yml` runs every 30 minutes after repository secrets are set:
- `OPENAI_API_KEY`
- `CLAWGIG_API_KEY`

Set repository variable `REVENUE_MACHINE_LIVE=1` to enable live bidding and delivery. Without it, the workflow is dry-run only.

## Deliberately not automated blindly

- financial transfers, purchases, lending, staking, or wallet movements
- identity/KYC or CAPTCHA circumvention
- off-platform communication/payment designed to bypass marketplace rules
- fake reviews, spam, mass unsolicited outreach
- jobs that prohibit AI
- client secrets uploaded to a model without permission
- legal/medical/financial decisions requiring an accountable human

The goal is **low-human-touch revenue, not account bans or bad deliveries**.
