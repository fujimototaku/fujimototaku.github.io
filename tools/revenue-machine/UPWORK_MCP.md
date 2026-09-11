# Upwork lane — official MCP

Upwork's official MCP server is the preferred high-liquidity agent channel because the platform itself exposes agent actions instead of relying on brittle browser RPA.

Official MCP endpoint:

`https://mcp.upwork.com/mcp`

Once connected by OAuth, the agent can search jobs, respond to invitations, submit proposals, review offers, and manage active contracts.

Use the same gates as CrowdWorks:
- fixed-price/objective deliverables first
- no mass proposals
- no fabricated experience
- no AI-prohibited jobs
- no off-platform payment or identity workarounds
- no action that spends money / buys Connects beyond a configured daily cap without operator approval
- only count platform-confirmed earnings

Recommended autonomous categories:
1. Python automation / integrations
2. data cleanup and extraction
3. small bug fixes with reproducible tests
4. AI workflow implementation
5. research outputs with explicit source requirements

Proposal policy: Astra writes only after an opportunity score >= 80 and expected gross margin remains positive after Connect cost, model cost, and platform fees.
