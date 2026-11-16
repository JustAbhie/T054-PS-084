# T054-PS-084 — Design Document

**Project:** ProcureFlow — Procurement Engine with Vendor Scoring, Quotation Comparison and Three-Way Match  
**Team:** T054  
**Problem statement:** PS-084  
**Implementation:** Python 3.10+; CSV-driven command processor; optional Streamlit reporting UI.

## 1. Purpose and scope

The system automates a procure-to-pay workflow: requisition registration and approval, RFQ and quotation evaluation, purchase-order creation, goods receipt, three-way invoice matching, debit-note adjustment and payment runs. It is command-file driven. The Streamlit dashboard is an additional presentation layer and is not the source of business decisions.

## 2. Glossary

| Term | Meaning |
|---|---|
| Requisition (REQ) | Internal request to purchase an item and quantity. |
| RFQ | Request for Quotation sent to invited vendors. |
| Quotation | Vendor's price, freight, currency, validity and delivery offer. |
| Landed cost | Per-unit purchase cost after freight, currency conversion and import customs. GST is excluded from vendor comparison. |
| PO | Purchase Order issued to the selected vendor. |
| GRN | Goods Receipt Note recording delivered, accepted and rejected quantities. |
| Three-way match | Validation of invoice data against the PO and accepted goods receipt balance. |
| Debit note | Amount recoverable from a vendor for quality-rejected goods; carried forward if it exceeds an invoice. |
| MSME | Micro, Small and Medium Enterprise supplier; receives the defined scoring and payment priority treatment. |
| HOLD | Invoice state used when one or more matching validations fail. |
| REMATCH | Re-runs matching for an invoice previously placed on HOLD. |
| FX rate | INR conversion rate for a foreign-currency quotation. |

## 3. Architecture and modules

- **Data layer (`data/`)** — vendor, item, requisition, RFQ, quotation, FX, distance, receipt and invoice CSV files, plus the ordered `commands.txt` event stream.
- **Workflow engine (`src/processor.py`)** — loads the CSV data, maintains procurement state, applies business rules, processes commands and exports result rows.
- **CLI (`main.py`)** — accepts input and output directory arguments and invokes the processor.
- **Dashboard (`ui/app.py`)** — displays generated outputs; it does not duplicate the business-rule calculations.
- **Tests (`tests/test_processor.py`)** — end-to-end and planted-edge-case regression checks.

### 3.1 Conceptual class/module diagram

```text
+--------------------+       +--------------------------+
|       main.py      |------>|   process(data, out)     |
| CLI / arguments    |       |  src/processor.py        |
+--------------------+       +------------+-------------+
                                          |
                       +------------------+-------------------+
                       |                  |                   |
                +------v------+    +------v------+     +------v------+
                | CSV Inputs  |    | Command     |     | Workflow    |
                | data/*.csv  |    | Dispatcher  |     | State       |
                +-------------+    +-------------+     +-------------+
                                          |
          +-------------------------------+-------------------------------+
          |              |                |              |                |
   +------v------+ +-----v------+ +-------v------+ +-----v------+ +-------v------+
   | Requisition | | RFQ/Quote  | | Purchase     | | GRN / Debit | | Invoice /    |
   | Approval    | | Evaluation | | Order        | | Note        | | Payment      |
   +-------------+ +------------+ +--------------+ +------------+ +--------------+
                                          |
                                  +-------v--------+
                                  | CSV Exports    |
                                  | outputs/*.csv  |
                                  +-------+--------+
                                          |
                                  +-------v--------+
                                  | Streamlit UI   |
                                  | ui/app.py      |
                                  +----------------+
```

The boxes represent logical responsibilities in the implementation, not separate deployed services or independent runtime classes.

## 4. Command processing and workflow states

The processor reads `commands.txt` sequentially. Blank lines and lines beginning with `#` are ignored. Each remaining line uses `COMMAND_NAME|arg1|arg2|...`. Event order is significant because later steps depend on earlier approvals, awards, receipts and invoice decisions.

### 4.1 Procurement lifecycle state diagram

```text
[Requisition Created]
          |
          v
[Approval Evaluation] -- insufficient authority --> [Pending / Refused]
          |
       approved
          v
      [RFQ Floated]
          |
          v
 [Quotations Validated]
          |
          v
 [Award Decision] ------ insufficient valid quotes ------> [Manual Award]
          |                                                   |
          +------------------------<--------------------------+
          |
          v
      [PO Created]
          |
          v
 [Goods Receipt(s)] --> [Partial / Accepted / Excess Returned / Quality Rejected]
          |
          v
   [Invoice Received]
          |
          v
   [Three-Way Match] -------- failed checks --------> [HOLD] -- REMATCH --> [Three-Way Match]
          |
        passed
          v
      [APPROVED]
          |
          v
   [Payment Eligible]
          |
      +---+----------------+
      |                    |
   within cash cap     cash cap reached
      |                    |
      v                    v
    [PAID]              [DEFERRED]
```

The diagram is a conceptual lifecycle. Actual output statuses and event rows are defined by the processor and the supplied data-pack output contract.

## 5. Business-rule register

| Rule ID | Rule | Implemented behavior / validation focus |
|---|---|---|
| BR-01 | Approval bands and split requisitions | Up to ₹50,000 is auto-approved; ₹50,001–₹5,00,000 requires MANAGER; above ₹5,00,000 requires DIRECTOR. Same-item requisitions in the preceding inclusive seven-day window are aggregated for the band. |
| BR-02 | Landed cost | Quoted freight is used when supplied; otherwise domestic freight is ₹2 × unit weight (kg) × state distance (km) / 100. Currency is converted to INR using the latest available rate on or before the quotation date. Imports attract 10% customs. GST is excluded from comparison. |
| BR-03 | Vendor score | Score out of 100: cost 50, on-time delivery 25, quality 15 and MSME bonus 10. Cost points are 50 × lowest landed cost / vendor landed cost; on-time points are history percentage / 4; quality points are max(0, 15 − rejection percentage). Score is rounded to two decimals. |
| BR-04 | Award and tie-break | Highest score wins only when its landed cost is within 5% of the lowest landed cost; otherwise the lowest landed cost wins. Ties prefer MSME, then earlier quotation timestamp. |
| BR-05 | Quotation validity and manual award | Quote must be received strictly before RFQ close and remain valid through at least close date + 15 days. For requisitions above ₹1,00,000, fewer than three valid quotes requires MANUAL_AWARD. |
| BR-06 | Goods receipt tolerance | Partial receipts are supported. Cumulative accepted quantity is capped at floor(105% of PO quantity); excess is returned. Quality-rejected quantity generates a debit note. |
| BR-07 | Three-way invoice matching | Invoice quantity cannot exceed accepted, not-yet-invoiced receipt quantity. Unit-price tolerance is the lower of 2% or ₹100. Invoice total tolerance is ₹500. Failed checks place the invoice on HOLD with reason codes. |
| BR-08 | Payment terms and MSME interest | Non-MSME due date is 30 days from invoice receipt; MSME due date is 45 days. MSME late interest uses 3 × 6.5% annual rate (19.5%) with monthly compounding as specified in the supplied data-pack rules. |
| BR-09 | Early-payment discount | 2% within 10 days of invoice approval and 1% within 20 days; discount is applied to the pre-GST value. |
| BR-10 | Debit-note adjustment | Quality rejection creates a debit note at PO unit price plus freight share. The balance is applied to the next approved invoice(s) for that vendor; any remainder carries forward. |
| BR-11 | Payment-run schedule and cash cap | Runs on Monday and Thursday; considers approved invoices due within the next seven days; MSME first, then due date. ₹25,00,000 cap applies; an invoice is deferred whole if it would exceed the cap, along with subsequent invoices in that run. |

## 6. Input and output contracts

The source data dictionary and command grammar are maintained in [`data/README.md`](../data/README.md). The engine exports the following files in `outputs/`:

| Output | Purpose |
|---|---|
| `requisition_log.csv` | Requisition and approval events, approval band and result. |
| `award_decisions.csv` | Per-quotation validation, FX, landed cost, score and award decision. |
| `purchase_orders.csv` | Generated PO details and award basis. |
| `receipts_log.csv` | Delivered, accepted, excess-returned and quality-rejected quantities and debit notes. |
| `match_results.csv` | Invoice match status, reason codes, debit-note application and due date. |
| `payment_runs.csv` | Per-invoice payment amount, discounts, interest and payment/defer status. |
| `processing_report.json` | Row counts and processing errors for the run. |

## 7. Test strategy and known limits

The automated tests run the full sample command stream and assert the principal planted boundaries, including split requisition escalation, strict RFQ close-time handling, 15-day quote validity, missing-date FX fallback, receipt cap, invoice tolerances, debit-note carry-forward, MSME interest and payment cash-limit deferral.

The sample pack explicitly states that it does not provide a complete expected-output set. Consequently, the current suite is a regression suite against documented scenarios; hidden evaluation parity has not been independently established. The design also records two command-format assumptions: PO date is derived from RFQ close date, and a rematch approval date is derived from the latest processed GRN date for that PO.

## 8. How to run

From the repository root, install `requirements.txt`, then run:

```bash
python main.py --data data --out outputs
python -m pytest -q
```

For the optional dashboard:

```bash
streamlit run ui/app.py
```
