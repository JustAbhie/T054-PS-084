# T054-PS-084 — ProcureFlow Procurement Engine

A Python procure-to-pay rules engine with a Streamlit dashboard. The project processes the supplied CSV master data and `commands.txt` in strict command-file order, then generates the six CSV outputs specified in the sample-data pack.

## Features

- Requisition registration, 7-day same-item aggregation, automatic approval thresholds and MANAGER/DIRECTOR approval controls.
- RFQ invitation and quotation validation, exchange-rate lookup with latest-earlier-rate fallback, computed freight, import customs, vendor scoring and award selection.
- Purchase-order generation, cumulative goods-receipt acceptance, 5% over-receipt ceiling and debit-note creation.
- Three-way invoice matching with quantity, price and total tolerances; HOLD reasons and rematching.
- Vendor-level debit-note carry-forward, payment due dates, early-payment discounts, MSME late interest and Monday/Thursday payment runs with a ₹25,00,000 cash ceiling.
- Streamlit dashboard for overview, vendors/items, requisitions, sourcing/awards, purchase orders, receipts, invoice matching and payment runs.

## Project Layout

```text
T054-PS-084/
├── data/                       # Supplied sample CSVs, README and commands.txt
├── docs/                       # Design notes, decision log and demo resources
├── outputs/                    # Generated evaluation CSVs and report
├── src/processor.py            # CSV-driven workflow engine
├── ui/app.py                   # Streamlit dashboard
├── tests/test_processor.py     # End-to-end and planted-edge-case tests
├── main.py                     # CLI entry point
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.10 or later
- pip
- Git (optional, for cloning the repository)

## Installation and Setup

### Windows (PowerShell / VS Code Terminal)

```powershell
git clone <https://github.com/JustAbhie/T054-PS-084/tree/main>
cd T054-PS-084

py -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### macOS / Linux (Terminal / VS Code Terminal)

```bash
git clone <https://github.com/JustAbhie/T054-PS-084/tree/main>
cd T054-PS-084

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Running the Procurement Engine

Execute the following command from the project root:

```bash
python main.py --data data --out outputs
```

The engine reads the input CSV datasets and processes `commands.txt` chronologically.

### Generated Outputs

The engine generates the following reports inside the `outputs/` directory:

| Output File | Description |
|---|---|
| `requisition_log.csv` | Requisition registration and approval events |
| `award_decisions.csv` | Quotation validation, landed costs, vendor scores and award decisions |
| `purchase_orders.csv` | Generated purchase orders |
| `receipts_log.csv` | Goods receipt, accepted quantities, excess returns and debit notes |
| `match_results.csv` | Invoice matching results, statuses and reason codes |
| `payment_runs.csv` | Payment processing, discounts, interest and payment status |
| `processing_report.json` | Processing summary, output counts and errors |

## Launching the Streamlit Dashboard

Run:

```bash
streamlit run ui/app.py
```

Streamlit opens the dashboard in your browser. Use the left navigation to move between procurement modules.

The dashboard provides:

- Procurement overview
- Vendor and item information
- Requisition and approval tracking
- RFQ sourcing and award decisions
- Purchase-order tracking
- Goods receipt monitoring
- Invoice matching and rematching
- Payment-run monitoring

The **Run & Export** page allows users to reprocess the command stream and download generated CSV outputs.

## Running Tests

Run the automated test suite from the project root:

```bash
pytest -q
```

The tests cover end-to-end processing and planted edge cases in the supplied sample-data pack.

## Sample-Data Validation Status

The supplied sample pack explicitly states that it does **not** contain expected-output CSVs. Therefore, this build has been executed against the complete sample command stream and checked against the planted scenarios documented in the sample README.

It has not been compared field-for-field with an official expected-output file or hidden evaluator dataset.

### Current Local Verification

- 180 command lines are consumed in order (comments and blank lines ignored).
- 39 requisition log events.
- 60 quotation decision rows.
- 20 purchase orders.
- 37 goods-receipt rows.
- 37 invoice match events (36 invoices plus one rematch).
- 30 payment-run invoice rows.
- 0 processing errors.
- 4 automated tests pass.

## Important Implementation Notes

- Missing FX dates use the latest earlier available rate, as specified by the sample-data README.
- Landed cost is calculated per unit and rounded to two decimals before scoring.
- The command stream does not carry explicit timestamps for `CLOSE_RFQ` or `REMATCH`; PO date uses the RFQ close date and rematch approval date uses the latest processed GRN date for that PO.
- This is an academic workflow prototype. The dashboard is a review and reporting layer; financial approvals and supplier payments must remain subject to authorized human controls.

## Documentation

- [System Design (Markdown)](docs/DESIGN.md)
- [System Design (PDF)](docs/DESIGN.pdf)
- [Decision Log](docs/DECISION_LOG.md)
- [Demo Video](docs/DEMO.md)
- [Demo Script](docs/DEMO_SCRIPT.md)

---

**Project ID:** T054-PS-084  
**Project:** ProcureFlow Procurement Engine  
**Technology:** Python, Pandas, Streamlit
