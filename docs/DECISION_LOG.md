# Decision log

| Area | Implemented behavior | Basis |
|---|---|---|
| Split requisitions | Sum same-item requisitions in the inclusive previous 7 × 24 hours | Sample-data README binding choice |
| Approval hierarchy | MANAGER can approve manager band; DIRECTOR can approve manager or director band | Role seniority; reject only a role below the required band |
| Quote close | Received timestamp must be strictly earlier than RFQ close | Sample-data README |
| Quote validity | Valid-until date must be at least close date + 15 days | Sample-data README |
| FX fallback | Latest earlier available rate; no earlier rate means invalid quote | Sample-data README |
| Freight | Use quoted freight per unit; otherwise ₹2 × unit weight × distance / 100 | Sample-data README |
| Customs | 10% of INR-converted (unit price + freight) for imports | Sample-data README |
| Landed cost | Per-unit landed cost, rounded to 2 decimals before scoring | Sample-data README |
| Receipt ceiling | Cumulative accepted quantity capped at floor(1.05 × PO quantity); quality rejects create debit notes, excess returns do not | Sample-data README |
| Match tolerances | Quantity against accepted receipt balance; price tolerance min(2%, ₹100); total tolerance ₹500 | Sample-data README |
| Debit notes | Apply to the next approved same-vendor invoice up to its invoice total; carry remainder | Sample-data README |
| Payment run | MSME first, then due date; if an invoice exceeds remaining cash, defer it and all later invoices in that run | Planted scenario EC-07 |
| MSME interest | 19.5% annual nominal rate compounded monthly using fractional 30-day periods | Sample-data README formula |
| PO date | RFQ close date, because the command stream has no award timestamp | Explicit implementation assumption |
| Rematch approval date | Latest processed GRN date for the PO, because REMATCH has no timestamp argument | Explicit implementation assumption; matches the planted INV-0019 scenario |

## Known validation boundary

The supplied data pack states that it contains no expected-output files. The project is tested against the README's documented planted scenarios and internal regression tests. Hidden evaluation parity remains unverified until an official expected-output set is supplied.
