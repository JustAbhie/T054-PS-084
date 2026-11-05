# Design overview

## Architecture

`src/processor.py` is the deterministic application service. It loads the supplied CSV tables, maintains the procure-to-pay state while consuming the command stream in order, and exports evaluation-format CSVs. `main.py` exposes the engine as a CLI. `ui/app.py` is a Streamlit presentation layer that reads the generated outputs and presents module-oriented views and charts.

## Processing sequence

1. Load vendor, item, requisition, RFQ, quotation, FX, receipt and invoice reference data.
2. Process requisition and approval events, aggregating same-item requisitions over the preceding inclusive 7 × 24-hour window.
3. Float and close RFQs; validate invited vendor, close timestamp, validity period and FX availability; calculate landed cost and vendor score; determine award or manual-award status.
4. Generate POs; apply cumulative receipt caps; create vendor debit-note balances for quality-rejected quantities.
5. Match invoices against accepted, not-yet-invoiced receipt quantities, PO price and GST-inclusive invoice total.
6. Apply debit notes when invoices become approved; preserve any remaining debit balance for the next approved invoice from that vendor.
7. Process scheduled payment runs in MSME-first and due-date order, with whole-invoice cash-limit deferral.

## Separation of concerns

- Business rules and workflow state: `src/processor.py`
- Command-line orchestration: `main.py`
- Presentation and navigation: `ui/app.py`
- Regression tests: `tests/test_processor.py`
- Source-defined data conventions and binding output format: `data/README.md`

The UI does not independently recalculate procurement decisions. It displays the engine's exported results to avoid duplicating business logic in the presentation layer.
