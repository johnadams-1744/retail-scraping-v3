# Retail Location Validation Agent

A prompt-engineered AI agent that takes a CSV of business names and websites, then researches each business to verify whether they operate physical retail locations suitable for Shopify POS outreach.

## What This Agent Does

The agent processes business lists through a three-phase funnel, doing the least work in the most efficient order:

**Phase 1 — Product Eligibility Screen** (fastest check, run on all businesses)
Visits each website, checks what products they sell, and immediately eliminates businesses with prohibited products (tobacco, nicotine, vapes, firearms, cannabis, pornography, etc.). This is the cheapest filter and removes the most businesses upfront.

**Phase 2 — Retail Location Verification** (eligible businesses only)
For businesses that pass Phase 1, determines whether they operate brand-owned retail locations. Filters out offices, coworking spaces, residential addresses, warehouses, third-party retailers/stockists, and online-only businesses.

**Phase 3 — Revenue Prediction & Ranking** (retail businesses only)
For the narrowed list of businesses with verified retail locations, does the deep research: estimates annual revenue based on product pricing, catalog depth, store footprint, location quality, and foot traffic signals. Ranks all qualified leads by outreach priority.

The final output is a single CSV containing all businesses (including eliminated ones with their elimination reason), sorted with the highest-priority qualified leads at the top.

## Files

| File | Purpose |
|---|---|
| `agent-prompt.md` | The full system prompt to paste into your AI agent |
| `sample-input.csv` | Example input CSV format (Business Name, Website) |
| `sample-output.csv` | Example of what the agent's output CSV looks like |

## How to Use

### 1. Set Up Your Agent

Copy the prompt from `agent-prompt.md` into your AI agent's system instructions. This prompt is designed for agents with web browsing capabilities (e.g., ChatGPT with browsing, Claude with tool use, Cursor Agent, or any agent framework with web access).

### 2. Prepare Your Input CSV

Your CSV needs exactly two columns:

```csv
Business Name,Website
Allbirds,https://allbirds.com
Warby Parker,https://warbyparker.com
```

### 3. Run the Agent

Upload your CSV and instruct the agent to process it. For large lists (100+ businesses), the agent will process in batches of 25.

### 4. Review the Output

The agent returns a CSV with these columns, sorted by outreach priority:

| Column | Description |
|---|---|
| Business Name | From your input |
| Web Domain | Cleaned domain |
| Eligible for Shopify Payments | Yes / No / Review Needed (Phase 1 result) |
| Eligibility Notes | Reason if ineligible |
| Has Retail Locations | TRUE / FALSE / UNKNOWN (Phase 2 result, blank if eliminated in Phase 1) |
| Number of Retail Locations | Integer count (blank if eliminated in Phase 1) |
| Location Details | Semicolon-separated addresses |
| Predicted Annual Revenue | Estimate with confidence (only for Phase 3 qualified leads) |
| Revenue Reasoning | How the estimate was derived (only for Phase 3 qualified leads) |
| Outreach Priority | Rank 1-N among qualified leads (blank for eliminated businesses) |
| Funnel Stage | Where the business exited: Phase 1/2/3 |

## Prompt Design Principles

This prompt was built following current AI agent prompt engineering best practices:

- **Structured sections with XML-style tags** — Role, objective, workflow, output format, rules, examples, and thinking protocol are cleanly separated for reliable parsing.
- **Three-phase funnel architecture** — The cheapest check (product eligibility) runs first on all businesses, eliminating the most rows. Retail location verification runs only on eligible businesses. Revenue estimation (the most expensive step) runs only on businesses with verified retail locations. This minimizes wasted effort and makes the agent reliable on large lists.
- **Chain-of-thought reasoning** — The `<thinking_protocol>` section forces the agent to reason through each business at each phase before committing to an output, reducing hallucination and improving accuracy.
- **Explicit inclusion/exclusion criteria** — Instead of vague instructions ("find real stores"), the prompt defines precise signals for what counts as a retail location and what doesn't, including the critical distinction between brand-owned stores and third-party stockists/retailers.
- **Concrete examples** — Four worked examples demonstrating elimination at each funnel stage (Phase 1 prohibited product, Phase 2 stockist-only, Phase 2 online-only, Phase 3 qualified lead) anchor the agent's understanding of expected output.
- **Guardrails and edge cases** — Rules cover inaccessible websites, approximate counts for large chains, the distinction between store hours vs. support hours, and by-appointment showrooms.
- **Structured output schema** — A fixed CSV schema with typed columns ensures consistent, machine-readable output.

## Customization

- **Add/remove prohibited categories** — Edit the list in Step 3 of the prompt to match your specific compliance requirements.
- **Adjust revenue estimation** — Modify the signals in Step 4 or add industry-specific benchmarks relevant to your target verticals.
- **Change output columns** — Add fields (e.g., "Store Type", "Neighborhood Quality Score") by editing the `<output_format>` section and updating the examples to match.
- **Batch size** — Change the batch size in `<final_instruction>` if your agent handles more or fewer rows efficiently.
