# Retail Location Validation Agent

A prompt-engineered AI agent that takes a CSV of business names and websites, then researches each business to verify whether they operate physical retail locations suitable for Shopify POS outreach.

## What This Agent Does

1. **Verifies retail locations** — Checks each business for physical storefronts, showrooms, or galleries where customers can shop in person. Filters out offices, coworking spaces, residential addresses, and warehouses.
2. **Counts locations** — Determines how many distinct retail locations each business operates.
3. **Estimates revenue** — Produces a predicted annual revenue figure based on product pricing, catalog depth, store footprint, location quality, and foot traffic signals.
4. **Screens for Shopify Payments eligibility** — Flags businesses selling prohibited products (tobacco, nicotine, vapes, firearms, cannabis, pornography, etc.) that would be ineligible for Shopify Payments.
5. **Exports a structured CSV** — Delivers a clean, actionable report the sales team can work from immediately.

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

The agent returns a CSV with these columns:

| Column | Description |
|---|---|
| Business Name | From your input |
| Web Domain | Cleaned domain |
| Has Retail Locations | TRUE / FALSE / UNKNOWN |
| Number of Retail Locations | Integer count |
| Location Details | Semicolon-separated addresses |
| Predicted Annual Revenue | Estimate with confidence level |
| Revenue Reasoning | How the estimate was derived |
| Eligible for Shopify Payments | Yes / No / Review Needed |
| Eligibility Notes | Reason if ineligible |

## Prompt Design Principles

This prompt was built following current AI agent prompt engineering best practices:

- **Structured sections with XML-style tags** — Role, objective, workflow, output format, rules, examples, and thinking protocol are cleanly separated for reliable parsing.
- **Chain-of-thought reasoning** — The `<thinking_protocol>` section forces the agent to reason through each business before committing to an output, reducing hallucination and improving accuracy.
- **Explicit inclusion/exclusion criteria** — Instead of vague instructions ("find real stores"), the prompt defines precise signals for what counts as a retail location and what doesn't.
- **Concrete examples** — Three worked examples (retail store, online-only, prohibited product) anchor the agent's understanding of expected output.
- **Guardrails and edge cases** — Rules cover inaccessible websites, approximate counts for large chains, the distinction between store hours vs. support hours, and by-appointment showrooms.
- **Structured output schema** — A fixed CSV schema with typed columns ensures consistent, machine-readable output.

## Customization

- **Add/remove prohibited categories** — Edit the list in Step 3 of the prompt to match your specific compliance requirements.
- **Adjust revenue estimation** — Modify the signals in Step 4 or add industry-specific benchmarks relevant to your target verticals.
- **Change output columns** — Add fields (e.g., "Store Type", "Neighborhood Quality Score") by editing the `<output_format>` section and updating the examples to match.
- **Batch size** — Change the batch size in `<final_instruction>` if your agent handles more or fewer rows efficiently.
