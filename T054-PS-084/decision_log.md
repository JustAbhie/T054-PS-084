# Decision log

1. Python 3.10+ chosen for a dependency-free command-line implementation.
2. Monetary values use `float` only for this prototype; production should use `Decimal`.
3. Rule methods are deterministic and return statuses/reasons rather than print internally.
4. POs track accepted and rejected quantities separately to support partial receipts.
5. A debit balance is retained by vendor when a debit note exceeds an invoice.
6. Award eligibility is filtered by the 5% landed-cost window before score ranking.
7. Payment runs skip an invoice that would exceed the cash cap rather than make a partial payment.
8. Sample input is JSON because it is easy to validate and reproduce in tests.
