# Five-minute demo walkthrough

## 1. Introduction (0:00–0:30)

Open the project in VS Code and show the project structure.

**Say:** “Hello everyone. Today, I'm presenting our Procurement Engine with Vendor Scoring, Quotation Comparison and Three-Way Matching. The system automates the complete procurement process, starting from purchase requisitions and ending with vendor payments. It applies predefined business rules at every stage to make procurement more efficient, transparent and reliable.”

## 2. Running the Engine (0:30–0:55)

Open the terminal and run:

```bash
python main.py --data data --out outputs
```

**Say:** “To execute the system, we run this command. The engine reads the input datasets, processes the commands chronologically and generates six output reports.”

Show the terminal row counts and `Processing errors: 0`. Explain that this confirms the sample workflow completed and the six reports were generated.

## 3. Requisition and Approval (0:55–1:30)

Open `outputs/requisition_log.csv`.

**Say:** “The process begins with a purchase requisition containing details such as the item, quantity, estimated price and department. The system automatically determines the required approval level based on purchase value. It also checks for split requisitions, where multiple requests for the same item are raised within seven days to avoid bypassing approval limits. For example, REQ-0006 has a combined value of ₹5.2 lakh. A manager's approval was refused because the required authority was Director level. The Director subsequently approved it.”

Show the REQ-0006 rows: `PENDING_APPROVAL`, `REFUSED_INSUFFICIENT_ROLE` and `APPROVED`.

## 4. RFQ and Vendor Evaluation (1:30–2:20)

Open `outputs/award_decisions.csv`.

**Say:** “After requisition approval, the system moves to the Request for Quotation stage. Vendors submit quotations containing unit price, freight charges, currency and validity details. The engine validates these quotations and calculates landed cost, considering freight, currency conversion and applicable import duty. Vendors are evaluated using four parameters: cost 50 points, delivery performance 25 points, quality 15 points and MSME status 10 points. The highest-scoring vendor is selected if its landed cost is within 5% of the lowest quotation. Otherwise, the system selects the vendor offering the lowest landed cost.”

Show vendor scores, landed costs and award decisions.

## 5. Purchase Order (2:20–2:40)

Open `outputs/purchase_orders.csv`.

**Say:** “Once the vendor is selected, the system automatically generates a Purchase Order. The PO contains the selected vendor, item, quantity, unit price, freight charges, order date and expected delivery date. This creates a formal record of the purchase agreement.”

Show one PO row.

## 6. Goods Receipt (2:40–3:15)

Open `outputs/receipts_log.csv`.

**Say:** “When the goods arrive, the receiving team records a Goods Receipt Note, or GRN. The system checks the delivered quantity and quality. It allows a maximum cumulative receipt of 5% above the ordered quantity. Any excess quantity is not accepted, while quality-rejected items are recorded separately. If goods are rejected due to quality issues, the system calculates a debit note against the vendor.”

Show accepted, rejected, excess and debit-note fields.

## 7. Three-Way Invoice Matching (3:15–4:05)

Open `outputs/match_results.csv`.

**Say:** “After receiving the goods, the vendor submits an invoice. The system performs three-way matching by comparing the Purchase Order, Goods Receipt Note and vendor invoice. It checks whether invoiced quantity matches accepted quantity, whether unit price is within the permitted tolerance and whether the invoice total is correct. If everything matches, the invoice is approved. Otherwise, it is placed on HOLD with a specific reason code. For example, a price difference can generate PRICE_VARIANCE. The system also supports rematching after discrepancies are corrected.”

Show invoice ID, matching status and reason codes.

## 8. Payment Processing (4:05–4:40)

Open `outputs/payment_runs.csv`.

**Say:** “Finally, the system processes vendor payments. Payment runs are scheduled for Mondays and Thursdays. MSME vendors receive priority, and the system considers invoice due dates. It also applies early-payment discounts where eligible and calculates late-payment interest for MSME vendors. A payment run has a total limit of ₹25 lakh. If the remaining payment limit is insufficient, the invoice and subsequent invoices are deferred rather than exceeding the limit. Debit notes are also adjusted during invoice approval.”

Show payment amount, vendor, discount, interest and payment status.

## 9. Conclusion (4:40–5:00)

Return to the project structure or generated output folder.

**Say:** “To conclude, our Procurement Engine automates the complete procurement lifecycle, from requisition creation to vendor payment. It combines approval validation, vendor evaluation, purchase order generation, goods receipt, three-way invoice matching and payment processing. By implementing these business rules, the system improves transparency, reduces manual errors and makes procurement more reliable. Thank you.”
