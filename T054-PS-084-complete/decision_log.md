# Decision log

1. Python 3.10+ standard library only keeps the project runnable without network access.
2. `Decimal` avoids binary floating-point errors for money and scores.
3. JSON supports ordered commands and timestamps without a database or UI.
4. Invalid outcomes produce explicit codes or statuses rather than silent corrections.
5. The 5% award filter is applied before ranking by score.
6. Debit notes remain vendor balances, allowing carry-forward beyond one invoice.
7. An over-limit payment is deferred; it is never partially paid.
8. `unittest` keeps the test suite runnable in a clean Python installation.
