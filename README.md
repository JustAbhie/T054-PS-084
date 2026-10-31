# T054-PS-084 - Procurement Engine
Capstone Project – Procurement Engine with Vendor Scoring, Quotation Comparison and Three-Way Match

A complete, dependency-free Python 3.10+ implementation of the PS-084 procure-to-pay capstone. JSON goes in and audit-friendly JSON decisions come out.

## What it does

- Registers vendors, items, and performance information.
- Approves requisitions, including same-item split detection across seven days.
- Validates quotations, calculates landed cost, scores vendors, and makes constrained award decisions.
- Tracks POs and full, partial, over, and rejected receipts.
- Performs three-way invoice matching with explicit hold reasons and debit-note netting.
- Calculates terms, early-payment discounts, MSME interest, and cash-limited payment runs.

## Run the complete example

```bash
cd /Users/afifaameen/Documents/Codex/2026-10-31/pl/outputs/T054-PS-084-complete
python3 -m p2p_engine.cli examples/full_demo.json --output examples/full_demo_output.json
cat examples/full_demo_output.json
```

## Run tests

```bash
python3 -m unittest discover -s tests -v
```

No third-party package is required. `examples/full_demo.json` documents the input JSON schema and supported operation sequence.

## Layout

- `p2p_engine/` - domain model, rule engine, JSON conversion, and CLI.
- `examples/` - runnable end-to-end scenario and generated output.
- `tests/` - unit tests for every rule and stated edge case.
- `design.md` - architecture and business-rule register.
- `decision_log.md` - implementation decisions.
