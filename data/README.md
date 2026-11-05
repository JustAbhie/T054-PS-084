# PS-084 – Procurement Engine with Vendor Scoring, Quotation Comparison and Three-Way Match — Sample Data Pack

Prepared by 10 SECONDS for Team T054.

## Files

| File | What it holds | Row count |
|---|---|---|
| `vendors.csv` | 12 vendors (MSME flag, state/country, currency, categories supplied, delivery and quality history) | 12 data rows |
| `state_distances.csv` | Road distance from the buyer's Bengaluru plant per vendor state (for computed freight) | 9 data rows |
| `items.csv` | 30 items with category, unit weight, GST rate and reference price | 30 data rows |
| `fx_rates.csv` | INR reference rates for USD and EUR on working days (weekends and 2026-10-02 have no row) | 138 data rows |
| `requisitions.csv` | 20 purchase requisitions over Aug-Sep 2026 | 20 data rows |
| `rfqs.csv` | One RFQ per requisition with close timestamp and invited vendors | 20 data rows |
| `quotations.csv` | Vendor quotations | 60 data rows |
| `goods_receipts.csv` | Goods receipts against POs (PO id = RFQ id with prefix PO) | 37 data rows |
| `invoices.csv` | Supplier invoices against POs | 36 data rows |
| `commands.txt` | Requisition approvals, RFQ float/close, manual awards, receipts, invoices, re-matches and Monday/Thursday payment runs | 180 command lines (excluding comments) |

Row numbers quoted below are 1-based data-row numbers (the header is row 0). Line numbers for `commands.txt` are physical line numbers including comment lines.

## Column reference

Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 means 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. An empty cell means "not applicable" and only occurs in columns whose notes say so.

### `vendors.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| vendor_id | string | VEN-nn | — | — |
| vendor_name | string | — | — | — |
| msme | bool | — | — | 10-point bonus; 45-day payment rule |
| vendor_type | enum | — | DOMESTIC, IMPORT | IMPORT attracts 10% customs |
| country | string | — | — | — |
| state | string | — | state_distances.csv | empty for IMPORT |
| currency | enum | — | INR, USD, EUR | quotation currency |
| gstin | string | 15 chars | — | empty for IMPORT |
| categories | string | ';'-separated | RAW, ELEC, PACK, MRO, IT | vendor is eligible (invited) for items of these categories |
| ontime_pct | decimal | % | 0-100 | on-time delivery history -> score = ontime_pct / 4 |
| rejection_pct | decimal | % | — | quality rejection history -> score = 15 - rejection_pct, floor 0 |

### `state_distances.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| state | string | — | — | — |
| distance_km | int | km | — | freight = Rs 2 per kg per 100 km x unit_weight_kg |

### `items.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| item_id | string | ITM-nnn | — | — |
| description | string | — | — | — |
| category | enum | — | RAW, ELEC, PACK, MRO, IT | — |
| uom | string | — | — | — |
| unit_weight_kg | decimal | kg | — | per unit |
| gst_pct | decimal | % | 12.0, 18.0 | printed, excluded from comparison |
| specification | string | — | — | — |
| reference_price | decimal | Rs | — | last purchase price; informational |

### `fx_rates.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| rate_date | date | — | — | working days only |
| currency | enum | — | USD, EUR | — |
| inr_per_unit | decimal | Rs | — | 4 decimals |

### `requisitions.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| req_id | string | REQ-nnnn | — | — |
| req_ts | timestamp | — | — | — |
| item_id | string | — | items.csv | — |
| quantity | int | — | — | — |
| est_unit_price | decimal | Rs | — | — |
| est_value | decimal | Rs | — | quantity x est_unit_price; decides the approval band |
| department | string | — | — | — |
| requested_by | string | — | — | — |
| need_by_date | date | — | — | — |

### `rfqs.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| rfq_id | string | RFQ-nnnn | — | same number as its requisition's position |
| req_id | string | — | requisitions.csv | — |
| issued_ts | timestamp | — | — | — |
| close_ts | timestamp | — | — | quotation must be received strictly before this |
| invited_vendors | string | ';'-separated vendor_ids | vendors.csv | quotes from vendors not listed are invalid |

### `quotations.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| quote_id | string | QT-nnnn | — | numbered in received order |
| rfq_id | string | — | rfqs.csv | — |
| vendor_id | string | — | vendors.csv | — |
| received_ts | timestamp | — | — | also the exchange-rate date |
| currency | enum | — | INR, USD, EUR | — |
| unit_price | decimal | in quote currency | — | excl. GST |
| freight_per_unit | decimal | in quote currency | — | empty = compute from distance (domestic only) |
| valid_until | date | — | — | must be >= close date + 15 days |
| delivery_days | int | days | — | PO due date = award date + delivery_days |

### `goods_receipts.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| grn_id | string | GRN-nnnn | — | — |
| grn_ts | timestamp | — | — | — |
| po_id | string | PO-nnnn | — | PO number = RFQ number |
| vendor_id | string | — | vendors.csv | — |
| delivered_qty | int | — | — | physically delivered |
| quality_rejected_qty | int | — | — | rejected at inspection -> debit note |
| remarks | string | — | — | — |

### `invoices.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| invoice_id | string | INV-nnnn | — | internal id |
| vendor_invoice_no | string | — | — | — |
| vendor_id | string | — | vendors.csv | — |
| po_id | string | — | — | — |
| invoice_date | date | — | — | — |
| received_date | date | — | — | payment terms count from here |
| quantity | int | — | — | — |
| unit_price | decimal | Rs | — | — |
| taxable_value | decimal | Rs | — | pre-GST value (discount base) |
| gst_amount | decimal | Rs | — | — |
| invoice_total | decimal | Rs | — | — |

## Command file format

`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands must be processed strictly in file order. Lines starting with `#` are comments and blank lines are ignored. An empty argument (two pipes in a row) means "not supplied". Every command used in this pack:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| `RAISE_REQ` | `req_id` | Register the requisition, apply split detection (same item within 7 days) and decide the approval band |
| `APPROVE_REQ` | `req_id|role|approver_name` | Approval by MANAGER or DIRECTOR; refused if the role is below the band |
| `FLOAT_RFQ` | `rfq_id` | Issue the RFQ to its invited vendors (requisition must be approved) |
| `CLOSE_RFQ` | `rfq_id` | Validate its quotations, compute landed cost and scores, award (PO created with po_id = PO-nnnn) or MANUAL_AWARD |
| `MANUAL_AWARD` | `rfq_id|vendor_id|approver|reason` | Award an RFQ left in MANUAL_AWARD |
| `RECEIVE_GRN` | `grn_id` | Apply a goods receipt (tolerance, rejection, debit note) |
| `RECEIVE_INVOICE` | `invoice_id` | Three-way match; APPROVED or HOLD with reason codes |
| `REMATCH` | `invoice_id` | Re-run the match for a HOLD invoice (approval date = this date if it passes) |
| `PAYMENT_RUN` | `YYYY-MM-DD` | Pay APPROVED invoices due within 7 days: MSME first, then due date; stop at the Rs 25,00,000 cash limit |

## Planted scenarios

Every edge case in the brief, mapped to the exact record where it occurs, followed by extra traps.

- **EC-01 Two requisitions of Rs 2,60,000 each for the same item 6 days apart - combined band DIRECTOR**
  - REQ-0002 (ITM-002, Rs 2,60,000) is MANAGER-band and approved; REQ-0006 for the same item 6 days later (Rs 2,60,000) makes the 7-day combined value Rs 5,20,000 -> DIRECTOR band: the MANAGER approval on line 20 must be refused, the DIRECTOR approval on line 26 accepted — `requisitions.csv REQ-0002 (row 2); requisitions.csv REQ-0006 (row 5); commands.txt lines 7, 20, 26`
- **EC-02 Quotation received 1 second before RFQ close with validity of exactly 15 days**
  - RFQ-0007 closes 2026-08-19 17:00:00; QT-0024 arrives at 2026-08-19 16:59:59 (1 second before close) with valid_until 2026-09-03 = close date + exactly 15 days -> VALID. QT-0025 arrives exactly at the close timestamp -> not 'before close' -> INVALID — `rfqs.csv RFQ-0007 (row 7); quotations.csv QT-0024 (row 24); quotations.csv QT-0025 (row 25)`
- **EC-03 Over-receipt of exactly 5.0 percent**
  - GRN-0018 on PO-0014 (PO qty 200) delivers 210 = exactly +5.0% -> all 210 accepted; the invoice for 210 matches — `goods_receipts.csv GRN-0018 (row 18)`
- **EC-04 Invoice price 2 percent higher when 2 percent is Rs 120 - Rs 100 rule applies**
  - INV-0028 bills unit price 6,120.00 against PO price 6,000.00 (PO-0018): +2% = Rs 120 but the tolerance is min(2%, Rs 100) = Rs 100 -> HOLD with reason PRICE_VARIANCE — `invoices.csv INV-0028 (row 28)`
- **EC-05 MSME invoice reaching day 45 on a Sunday - interest starts day 46**
  - INV-0019 (MSME vendor VEN-11) received 2026-09-10; day 45 = 2026-10-25 (Sunday). It is on HOLD (QTY_EXCEEDS_RECEIPT: billed 60 vs 30 received) until the balance GRN-0037 arrives and the REMATCH on line 180 approves it on Saturday 2026-10-24; the next run is Monday 2026-10-26 = day 46 -> 1 day of interest at 19.5% p.a. compounded monthly (no shift for the Sunday), plus the 2% early-payment discount (paid 2 days after approval) — `invoices.csv INV-0019 (row 19); goods_receipts.csv GRN-0037 (row 37); commands.txt line 180`
- **EC-06 Debit note larger than the next invoice - carry remainder**
  - GRN-0012 rejects 40 units on PO-0008 -> debit note 40 x (PO price 3900.00 + freight share 19.50) = Rs 156780.00. The next approved invoice of VEN-09 is INV-0015 (total Rs 61360.00) -> netted to 0.00, remainder Rs 95420.00 carried to INV-0017 — `goods_receipts.csv GRN-0012 (row 12); invoices.csv INV-0015 (row 15); invoices.csv INV-0017 (row 17)`
- **EC-07 Payment run cash limit hit mid-invoice - invoice deferred, not partially paid**
  - PAYMENT_RUN 2026-10-15: cumulative payable reaches Rs 1799221.93; the next invoice INV-0026 (payable Rs 801692.00) would cross the Rs 25,00,000 limit -> deferred whole (not part-paid) together with everything after it; it is paid in the run of 2026-10-19 — `invoices.csv INV-0026 (row 26); commands.txt line 174`
- **EC-08 Import quotation whose exchange-rate date is missing from the table**
  - QT-0060 from import vendor VEN-05 is dated 2026-10-02 (Gandhi Jayanti) — fx_rates.csv has no USD rate for that date -> use the latest earlier rate (2026-10-01); customs 10% on (price + freight) in INR — `quotations.csv QT-0060 (row 60); rfqs.csv RFQ-0020 (row 20)`
- **Extra traps (not in the brief, but realistic):**
  - RFQ-0001: highest score is QT-0006 but its landed cost is ~7% above the lowest -> outside the 5% window -> the lowest landed cost (QT-0005) wins — `rfqs.csv RFQ-0001 (row 1); quotations.csv QT-0006 (row 6); quotations.csv QT-0005 (row 5)`
  - RFQ-0003 (> Rs 1,00,000): QT-0009 is valid only 14 days after close -> invalid; only 2 valid quotations remain -> MANUAL_AWARD, resolved by the MANUAL_AWARD command on line 35 — `rfqs.csv RFQ-0003 (row 3); quotations.csv QT-0009 (row 9); commands.txt line 35`
  - GRN-0006 on PO-0005 delivers 32 in its first lot: cumulative receipt exceeds 105% of the PO quantity by 1 unit -> that unit REJECTED and returned (no debit note) — `goods_receipts.csv GRN-0006 (row 6)`
  - INV-0011: invoice_total is Rs 500.01 more than quantity x unit price + GST -> HOLD with TOTAL_MISMATCH (Rs 500.00 would pass) — `invoices.csv INV-0011 (row 11)`

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation

Produce these CSV files (header row, same conventions as above, rows sorted as stated). Where the brief is silent on a format detail the choice below is binding for evaluation.

### `requisition_log.csv`

One row per RAISE_REQ / APPROVE_REQ, in command order.

Columns, in order: `req_id`, `event`, `own_value`, `combined_value`, `band_required`, `role`, `result`

### `award_decisions.csv`

One row per quotation per RFQ (in quote_id order), then the decision on the winning row.

Columns, in order: `rfq_id`, `quote_id`, `vendor_id`, `valid`, `invalid_reason`, `fx_rate_date`, `fx_rate`, `landed_cost_per_unit`, `cost_points`, `ontime_points`, `quality_points`, `msme_points`, `score`, `decision`

### `purchase_orders.csv`

One row per PO.

Columns, in order: `po_id`, `rfq_id`, `vendor_id`, `item_id`, `quantity`, `unit_price`, `freight_per_unit`, `po_date`, `due_date`, `award_basis`

### `receipts_log.csv`

One row per GRN.

Columns, in order: `grn_id`, `po_id`, `delivered_qty`, `accepted_qty`, `excess_returned_qty`, `quality_rejected_qty`, `debit_note_id`, `debit_note_amount`, `line_status`

### `match_results.csv`

One row per RECEIVE_INVOICE / REMATCH.

Columns, in order: `invoice_id`, `event_date`, `status`, `reason_codes`, `debit_note_applied`, `due_date`

### `payment_runs.csv`

One row per invoice considered in each run, in payment order.

Columns, in order: `run_date`, `invoice_id`, `vendor_id`, `msme`, `due_date`, `invoice_total`, `debit_note_applied`, `discount`, `interest`, `amount_paid`, `status`

Binding choices where the brief is silent: a requisition's combined value is the sum of requisitions for the same item raised within the previous 7 x 24 hours (inclusive of itself). Missing fx date -> latest earlier rate. Landed cost per unit = (unit_price + freight) x fx (+10% customs on that sum for IMPORT), rounded to 2 decimals before scoring; cost_points = 50 x lowest/own. Within-5% test: winner's landed <= 1.05 x lowest. MANUAL_AWARD applies when est_value > 1,00,000 and valid quotes < 3. Receipt: accepted = min(delivered - quality_rejected, floor(1.05 x PO qty) - already accepted); the rest is excess_returned_qty (no debit note). Debit note = quality_rejected x (PO price + freight_per_unit), no GST. Three-way match reason codes QTY_EXCEEDS_RECEIPT (invoice qty > accepted - already approved qty), PRICE_VARIANCE (|invoice - PO price| > min(2% of PO price, Rs 100)), TOTAL_MISMATCH (|invoice_total - round(qty x unit_price x (1 + GST))| > Rs 500), joined with ';'. Debit-note balance is netted at approval (up to the invoice total). Due date = received_date + 30 (non-MSME) or + 45 (MSME). Discount on taxable_value: 2% if run_date - approval_date <= 10 days, 1% if <= 20. MSME interest = (invoice_total - debit_note_applied) x ((1 + 0.195/12)^(days_late/30) - 1), days_late = run_date - due_date. `status` PAID or DEFERRED_CASH_LIMIT. `decision` AWARDED_TOP_SCORE, AWARDED_LOWEST_LANDED, MANUAL_AWARD or empty.
