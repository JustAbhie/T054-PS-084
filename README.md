# T054-PS-084 — ProcureFlow Procurement Engine

A Python procure-to-pay rules engine with a Streamlit dashboard. The project processes the supplied CSV master data and `commands.txt` in strict command-file order, then generates the six CSV outputs specified in the sample-data pack.

## Features

- Requisition registration, 7-day same-item aggregation and MANAGER/DIRECTOR approval controls.
- RFQ invitation and quotation validation, exchange-rate lookup with latest-earlier-rate fallback, computed freight, import customs, vendor scoring and award selection.
- Purchase-order generation, cumulative goods-receipt acceptance, 5% over-receipt ceiling and debit-note creation.
- Three-way invoice matching with quantity, price and total tolerances; HOLD reasons and rematching.
- Vendor-level debit-note carry-forward, payment due dates, early-payment discounts, MSME late interest and Monday/Thursday payment runs with a ₹25,00,000 cash ceiling.
- Streamlit dashboard for overview, vendors/items, requisitions, sourcing/awards, purchase orders, receipts, invoice matching and payment runs.

## Project layout

```text
T054-PS-084/
├── data/                       # Supplied sample CSVs, README and commands.txt
├── docs/                       # Design notes and decision log
├── outputs/                    # Generated evaluation CSVs and report
├── src/processor.py            # CSV-driven workflow engine
├── ui/app.py                   # Streamlit dashboard
├── tests/test_processor.py     # End-to-end and planted-edge-case tests
├── main.py                     # CLI entry point
└── requirements.txt
```

## Run on macOS (VS Code / Terminal)

Python 3.10 or later is recommended.

```bash
cd T054-PS-084
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Run the procurement engine

```bash
python main.py --data data --out outputs
```

The engine writes:

- `outputs/requisition_log.csv`
- `outputs/award_decisions.csv`
- `outputs/purchase_orders.csv`
- `outputs/receipts_log.csv`
- `outputs/match_results.csv`
- `outputs/payment_runs.csv`
- `outputs/processing_report.json`

### Launch the UI/UX dashboard

```bash
streamlit run ui/app.py
```

Streamlit opens the dashboard in your browser. Use the left navigation to move between procurement modules. The Run & Export page lets you reprocess the command stream and download generated CSV outputs.

### Run tests

```bash
pytest -q
```

## Sample-data validation status

The supplied sample pack explicitly states that it does **not** contain expected-output CSVs. Therefore, this build has been executed against the complete sample command stream and checked against the planted scenarios documented in the sample README; it has not been compared field-for-field with an official expected-output file or hidden evaluator dataset.

Current local verification:

- 180 command lines are consumed in order (comments and blank lines ignored).
- 39 requisition log events.
- 60 quotation decision rows.
- 20 purchase orders.
- 37 goods-receipt rows.
- 37 invoice match events (36 invoices plus one rematch).
- 30 payment-run invoice rows.
- 0 processing errors.
- 3 automated tests pass, including the planted boundary scenarios.

## Important implementation notes

- Missing FX dates use the latest earlier available rate, as bound by the sample-data README.
- Landed cost is calculated per unit and rounded to two decimals before scoring.
- The command stream does not carry explicit timestamps for `CLOSE_RFQ` or `REMATCH`; PO date uses the RFQ close date and rematch approval date uses the latest processed GRN date for that PO.
- This is an academic workflow prototype. The dashboard is a review and reporting layer; financial approvals and supplier payments must remain subject to authorized human controls.
