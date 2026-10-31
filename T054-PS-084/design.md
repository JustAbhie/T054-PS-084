# Design document - PS-084

## Glossary

RFQ: request for quotation. PO: purchase order. GRN: goods-receipt note. MSME: qualifying small enterprise. Three-way match: invoice compared to PO and accepted receipt.

## Domain flow

`Requisition -> approved -> RFQ -> valid quotations -> award -> PO -> receipt -> invoice match -> approved/hold -> payment run -> paid`

The engine stores vendors, items, requisitions, POs, invoices, and outstanding debit balances in memory. It is deliberately separated into domain models and a rule engine so it can later be backed by CSV/JSON files.

## Business-rule register

| ID | Rule / outcome |
|---|---|
| BR-01 | Approval band: <=50,000 AUTO; <=500,000 MANAGER; otherwise DIRECTOR; same-item requisitions within 7 days are combined. |
| BR-02 | Landed cost includes price, freight, import customs, and quotation-date conversion; GST excluded. |
| BR-03 | Score is cost 50 + OTD 25 + quality 15 + MSME 10, rounded to two decimals. |
| BR-04 | Highest scorer wins only within 5% of lowest landed cost; then MSME, then earlier quote break ties. |
| BR-05 | Quote must arrive by close and be valid 15 days afterward; <3 valid quotes over 100,000 is manual award. |
| BR-06 | Accept up to 105%; excess rejected and debited; close at >=95% after due date. |
| BR-07 | Invoice quantity <= accepted, unit price within min(2%, 100), and total within 500; otherwise HOLD with reasons. |
| BR-08 | Non-MSME is net 30; MSME net 45 then monthly-compounded interest at 3x 6.5%. |
| BR-09 | 2% discount within 10 days, 1% within 20 days, before GST. |
| BR-10 | Rejected quantity creates PO-price-plus-freight debit balance, net against next approved invoice. |
| BR-11 | Monday/Thursday run pays invoices due in 7 days: MSME first, then due date, to 25,00,000; no partial payment. |

## Explicit edge cases

Tests cover requisitions six days apart, exact 5% receipt, price tolerance where 2% exceeds 100, MSME day 45/day 46 boundary, payment cash limit, and missing FX rates. The engine returns `MISSING_EXCHANGE_RATE` for an imported quotation without a quotation-date rate.
