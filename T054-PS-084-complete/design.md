# PS-084 design document

## Architecture

`models` defines domain objects, `engine` owns rule execution and state, `io` maps JSON to validated objects, and `cli` runs operations in order. The application is file-driven and deliberately has no UI.

```text
Requisition -> Approval -> RFQ / Quotes -> Award -> Purchase Order
                                                  |
Receipt / GRN <-----------------------------------+
     |
Invoice -> Three-way match -> APPROVED or HOLD -> Payment run -> PAID
```

## Business-rule register

| ID | Implementation / observable result |
|---|---|
| BR-01 | Approval <=50,000 auto; <=500,000 manager; otherwise director. Same-item requisitions within seven days are combined. |
| BR-02 | Landed cost includes price, freight, import customs, and quote-date conversion; GST is excluded. |
| BR-03 | Score is cost 50 + on-time delivery 25 + quality 15 + MSME 10, rounded to two decimals. |
| BR-04 | Only quotes within 5% of cheapest compete by score; then MSME, then earlier timestamp break ties. |
| BR-05 | Quote must arrive by close and remain valid 15 days; <3 valid quotes above 1,00,000 is `MANUAL_AWARD`. |
| BR-06 | Up to 105% receipt is accepted; excess rejected; partials allowed; line closes at >=95% after due date. |
| BR-07 | Match needs invoice quantity <= accepted receipt, price within min(2%, 100), total within 500; failures become HOLD codes. |
| BR-08 | Non-MSME is net 30; MSME is net 45, then interest at 3x 6.5%, compounded monthly. |
| BR-09 | 2% discount within 10 days; 1% within 20 days. |
| BR-10 | Rejected receipt generates PO-price plus freight-share debit balance and carries forward. |
| BR-11 | Monday/Thursday run pays APPROVED invoices due in seven days: MSME first, then due date, under 25,00,000 with no partial payment. |

## Edge cases covered

Tests cover split requisitions six days apart, missing FX rates, exact 5% over-receipt, price tolerance capped at 100, MSME day-46 interest, debit carry-forward, and cash-limited deferred payment.

## Assumptions

Amounts are pre-GST. The provided distance table uses `vendor_state|buyer_state`; fallback freight is Rs 2/kg per 100 km. State is in-memory within a CLI run.
