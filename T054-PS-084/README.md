# T054-PS-084 - Procurement Engine

Command-line, file-driven procure-to-pay engine for vendor scoring, quotation comparison, three-way matching, and payment runs. It uses only Python's standard library at runtime.

## Run

```bash
python3 -m pip install -e '.[dev]'
python3 -m procurement.cli sample_data/demo.json
python3 -m pytest
```

The demo prints the vendor award decision. Tests cover approval bands, landed cost, scoring and award, receipts, invoice matching, debit notes, MSME interest, and payment-run cash limits.

## Project layout

- `procurement/engine.py` - business-rule implementation.
- `procurement/models.py` - domain entities.
- `sample_data/demo.json` - runnable quotation scenario.
- `tests/` - automated test suite.
- `design.md` - design and BR register.
- `decision_log.md` - implementation decisions.

## Important behaviour

Input is intentionally kept file-driven; no UI or framework is required. The engine returns explicit status/reason values for decisions such as `MANUAL_AWARD`, `HOLD`, and missing exchange-rate data. GST is intentionally outside comparison calculations, as specified.
