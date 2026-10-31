from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from .errors import ValidationError
from .models import Invoice, Item, PurchaseOrder, Quote, Requisition, Vendor

ZERO = Decimal("0")
MONEY = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


class ProcurementEngine:
    """In-memory reference implementation of the PS-084 business rules.

    It deliberately has no UI or database. State can be supplied from JSON and every
    decision is returned as structured data for files, tests, or a CLI consumer.
    """

    def __init__(self, buyer_state: str, distances: dict[tuple[str, str], Decimal] | None = None,
                 exchange_rates: dict[tuple[str, date], Decimal] | None = None) -> None:
        self.buyer_state = buyer_state
        self.distances = distances or {}
        self.exchange_rates = exchange_rates or {}
        self.vendors: dict[str, Vendor] = {}
        self.items: dict[str, Item] = {}
        self.requisitions: dict[str, Requisition] = {}
        self.purchase_orders: dict[str, PurchaseOrder] = {}
        self.invoices: dict[str, Invoice] = {}
        self.debit_balances: dict[str, Decimal] = {}

    def add_vendor(self, vendor: Vendor) -> None:
        self.vendors[vendor.vendor_id] = vendor

    def add_item(self, item: Item) -> None:
        self.items[item.item_id] = item

    # BR-01
    def approve_requisition(self, requisition: Requisition) -> str:
        self._require(requisition.item_id in self.items, "UNKNOWN_ITEM")
        split_total = sum((r.value for r in self.requisitions.values()
                           if r.item_id == requisition.item_id
                           and 0 <= (requisition.requested_on - r.requested_on).days <= 7), ZERO)
        combined = requisition.value + split_total
        requisition.approval_status = "AUTO_APPROVED" if combined <= Decimal("50000") else (
            "MANAGER_REQUIRED" if combined <= Decimal("500000") else "DIRECTOR_REQUIRED")
        self.requisitions[requisition.requisition_id] = requisition
        return requisition.approval_status

    # BR-02
    def landed_cost(self, quote: Quote) -> Decimal:
        self._require(quote.vendor_id in self.vendors, "UNKNOWN_VENDOR")
        self._require(quote.item_id in self.items, "UNKNOWN_ITEM")
        unit_price = quote.unit_price
        if quote.currency != "INR":
            rate = self.exchange_rates.get((quote.currency, quote.quoted_at.date()))
            if rate is None:
                raise ValidationError("MISSING_EXCHANGE_RATE")
            unit_price *= rate
        freight = quote.freight
        if freight is None:
            distance = self.distances.get((self.vendors[quote.vendor_id].state, self.buyer_state))
            if distance is None:
                raise ValidationError("MISSING_DISTANCE")
            freight = Decimal("2") * self.items[quote.item_id].weight_kg * quote.quantity * distance / Decimal("100")
        subtotal = unit_price * quote.quantity + freight
        return money(subtotal * (Decimal("1.10") if quote.is_import else Decimal("1")))

    # BR-03
    def vendor_score(self, quote: Quote, lowest_cost: Decimal) -> Decimal:
        vendor = self.vendors[quote.vendor_id]
        cost = self.landed_cost(quote)
        score = Decimal("50") * lowest_cost / cost
        score += vendor.on_time_delivery_pct / Decimal("4")
        score += max(ZERO, Decimal("15") - vendor.rejection_pct)
        score += Decimal("10") if vendor.is_msme else ZERO
        return money(score)

    # BR-04 and BR-05
    def award(self, quotes: Iterable[Quote], rfq_close: date) -> dict:
        valid = [q for q in quotes if q.quoted_at.date() <= rfq_close and q.valid_until >= rfq_close + timedelta(days=15)]
        if not valid:
            return {"status": "NO_VALID_QUOTES", "winner": None, "reason": "No quote met date and validity rules"}
        costs = {q.quote_id: self.landed_cost(q) for q in valid}
        cheapest = min(costs.values())
        if len(valid) < 3 and cheapest > Decimal("100000"):
            return {"status": "MANUAL_AWARD", "winner": None, "reason": "Fewer than 3 valid quotes above Rs 1,00,000"}
        eligible = [q for q in valid if costs[q.quote_id] <= cheapest * Decimal("1.05")]
        scores = {q.quote_id: self.vendor_score(q, cheapest) for q in eligible}
        winner = sorted(eligible, key=lambda q: (-scores[q.quote_id], not self.vendors[q.vendor_id].is_msme, q.quoted_at))[0]
        return {"status": "AWARDED", "winner": winner.vendor_id, "quote_id": winner.quote_id,
                "landed_cost": str(costs[winner.quote_id]), "score": str(scores[winner.quote_id])}

    def add_purchase_order(self, po: PurchaseOrder) -> None:
        self._require(po.vendor_id in self.vendors, "UNKNOWN_VENDOR")
        self._require(po.item_id in self.items, "UNKNOWN_ITEM")
        self.purchase_orders[po.po_id] = po

    # BR-06 and BR-10
    def receive_goods(self, po_id: str, quantity: Decimal, received_on: date) -> dict:
        po = self._po(po_id)
        self._require(quantity > ZERO, "RECEIPT_QUANTITY_MUST_BE_POSITIVE")
        remaining_allowed = po.quantity * Decimal("1.05") - po.accepted_quantity
        accepted = min(quantity, max(ZERO, remaining_allowed))
        rejected = quantity - accepted
        po.accepted_quantity += accepted
        po.rejected_quantity += rejected
        if po.accepted_quantity >= po.quantity * Decimal(".95") and received_on > po.due_date:
            po.status = "CLOSED"
        debit_note = money(rejected * po.unit_price + (rejected / po.quantity * po.freight)) if rejected else ZERO
        if debit_note:
            self.debit_balances[po.vendor_id] = self.debit_balances.get(po.vendor_id, ZERO) + debit_note
        return {"po_id": po_id, "accepted": str(accepted), "rejected": str(rejected),
                "debit_note": str(debit_note), "status": po.status}

    # BR-07 and BR-10
    def match_invoice(self, invoice: Invoice) -> dict:
        po = self._po(invoice.po_id)
        self._require(po.vendor_id == invoice.vendor_id, "INVOICE_VENDOR_DOES_NOT_MATCH_PO")
        reasons: list[str] = []
        if invoice.quantity > po.accepted_quantity:
            reasons.append("QUANTITY_EXCEEDS_ACCEPTED_RECEIPT")
        if abs(invoice.unit_price - po.unit_price) > min(po.unit_price * Decimal(".02"), Decimal("100")):
            reasons.append("UNIT_PRICE_OUTSIDE_TOLERANCE")
        if abs(invoice.total - po.expected_total) > Decimal("500"):
            reasons.append("TOTAL_OUTSIDE_TOLERANCE")
        invoice.hold_reasons = reasons
        if reasons:
            invoice.status = "HOLD"
        else:
            debit = min(self.debit_balances.get(invoice.vendor_id, ZERO), invoice.total)
            invoice.debit_applied = debit
            invoice.total -= debit
            self.debit_balances[invoice.vendor_id] = self.debit_balances.get(invoice.vendor_id, ZERO) - debit
            invoice.status, invoice.approved_on = "APPROVED", invoice.received_on
        self.invoices[invoice.invoice_id] = invoice
        return {"invoice_id": invoice.invoice_id, "status": invoice.status, "hold_reasons": reasons,
                "debit_applied": str(invoice.debit_applied), "payable_total": str(money(invoice.total))}

    # BR-08 and BR-09
    def due_date(self, invoice: Invoice) -> date:
        return invoice.received_on + timedelta(days=45 if self.vendors[invoice.vendor_id].is_msme else 30)

    def payment_amount(self, invoice: Invoice, payment_date: date, bank_rate: Decimal = Decimal(".065")) -> Decimal:
        self._require(invoice.status == "APPROVED", "INVOICE_NOT_APPROVED")
        approval_date = invoice.approved_on or invoice.received_on
        elapsed = (payment_date - approval_date).days
        value = invoice.total * (Decimal(".98") if elapsed <= 10 else Decimal(".99") if elapsed <= 20 else Decimal("1"))
        due = self.due_date(invoice)
        if self.vendors[invoice.vendor_id].is_msme and payment_date > due:
            # Daily pro-rata exponent supports an exact day-46 start and monthly compounding.
            value *= (Decimal("1") + Decimal("3") * bank_rate / Decimal("12")) ** (Decimal((payment_date - due).days) / Decimal("30"))
        return money(value)

    # BR-11
    def payment_run(self, run_date: date, cash_limit: Decimal = Decimal("2500000")) -> dict:
        self._require(run_date.weekday() in (0, 3), "PAYMENT_RUN_MUST_BE_MONDAY_OR_THURSDAY")
        candidates = [i for i in self.invoices.values() if i.status == "APPROVED" and self.due_date(i) <= run_date + timedelta(days=7)]
        candidates.sort(key=lambda i: (not self.vendors[i.vendor_id].is_msme, self.due_date(i), i.invoice_id))
        payments, spent = [], ZERO
        for invoice in candidates:
            amount = self.payment_amount(invoice, run_date)
            if spent + amount > cash_limit:
                continue  # Explicitly deferred; payment is never split.
            invoice.status = "PAID"
            spent += amount
            payments.append({"invoice_id": invoice.invoice_id, "vendor_id": invoice.vendor_id,
                             "amount": str(amount), "due_date": self.due_date(invoice).isoformat()})
        return {"run_date": run_date.isoformat(), "payments": payments, "total_paid": str(money(spent)),
                "cash_remaining": str(money(cash_limit - spent))}

    def _po(self, po_id: str) -> PurchaseOrder:
        if po_id not in self.purchase_orders:
            raise ValidationError("UNKNOWN_PURCHASE_ORDER")
        return self.purchase_orders[po_id]

    @staticmethod
    def _require(condition: bool, code: str) -> None:
        if not condition:
            raise ValidationError(code)
