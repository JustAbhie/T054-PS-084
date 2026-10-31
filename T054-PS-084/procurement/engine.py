from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import pow

from .models import Invoice, Item, PurchaseOrder, Quotation, Requisition, Vendor


@dataclass(frozen=True)
class Award:
    vendor_id: str | None
    status: str
    landed_cost: float | None
    score: float | None
    reason: str = ""


class ProcurementEngine:
    """In-memory implementation of the PS-084 rules. Monetary amounts are INR."""

    def __init__(self, distances: dict[tuple[str, str], int] | None = None,
                 exchange_rates: dict[tuple[str, date], float] | None = None) -> None:
        self.vendors: dict[str, Vendor] = {}
        self.items: dict[str, Item] = {}
        self.requisitions: list[Requisition] = []
        self.pos: dict[str, PurchaseOrder] = {}
        self.invoices: dict[str, Invoice] = {}
        self.debit_balances: dict[str, float] = {}
        self.distances = distances or {}
        self.exchange_rates = exchange_rates or {}

    def register_vendor(self, vendor: Vendor) -> None:
        self.vendors[vendor.id] = vendor

    def register_item(self, item: Item) -> None:
        self.items[item.id] = item

    def approve_requisition(self, req: Requisition) -> str:
        # BR-01: same item, seven-day split detection changes the band.
        recent = [r.value for r in self.requisitions if r.item_id == req.item_id
                  and 0 <= (req.created_on - r.created_on).days <= 7]
        band_value = req.value + sum(recent)
        req.approval = "AUTO" if band_value <= 50_000 else "MANAGER" if band_value <= 500_000 else "DIRECTOR"
        self.requisitions.append(req)
        return req.approval

    def landed_cost(self, quote: Quotation, buyer_state: str) -> float:
        # BR-02
        item = self.items[quote.item_id]
        price = quote.unit_price
        if quote.currency != "INR":
            rate = self.exchange_rates.get((quote.currency, quote.quoted_at.date()))
            if rate is None:
                raise ValueError("MISSING_EXCHANGE_RATE")
            price *= rate
        freight = quote.freight
        if freight is None:
            km = self.distances.get((self.vendors[quote.vendor_id].state, buyer_state))
            if km is None:
                raise ValueError("MISSING_DISTANCE")
            freight = 2 * item.weight_kg * quote.quantity * (km / 100)
        subtotal = price * quote.quantity + freight
        return round(subtotal * (1.10 if quote.imported else 1.0), 2)

    def vendor_score(self, quote: Quotation, buyer_state: str, lowest_cost: float) -> float:
        # BR-03
        v = self.vendors[quote.vendor_id]
        cost = self.landed_cost(quote, buyer_state)
        return round(50 * lowest_cost / cost + v.on_time_delivery_rate / 4
                     + max(0, 15 - v.quality_rejection_rate) + (10 if v.msme else 0), 2)

    def award(self, quotes: list[Quotation], rfq_close: date, buyer_state: str) -> Award:
        # BR-04 and BR-05
        valid = [q for q in quotes if q.quoted_at.date() <= rfq_close and q.valid_until >= rfq_close + timedelta(days=15)]
        if not valid:
            return Award(None, "NO_VALID_QUOTES", None, None)
        costs = {q.id: self.landed_cost(q, buyer_state) for q in valid}
        lowest = min(costs.values())
        if len(valid) < 3 and lowest > 100_000:
            return Award(None, "MANUAL_AWARD", None, None, "Fewer than three valid quotations")
        eligible = [q for q in valid if costs[q.id] <= lowest * 1.05]
        scores = {q.id: self.vendor_score(q, buyer_state, lowest) for q in eligible}
        ranked = sorted(eligible, key=lambda q: (-scores[q.id], not self.vendors[q.vendor_id].msme, q.quoted_at))
        winner = ranked[0]
        return Award(winner.vendor_id, "AWARDED", costs[winner.id], scores[winner.id])

    def create_po(self, po: PurchaseOrder) -> None:
        self.pos[po.id] = po

    def receive(self, po_id: str, quantity: float, received_on: date) -> dict:
        # BR-06
        po = self.pos[po_id]
        maximum = po.quantity * 1.05
        allowed = max(0, min(quantity, maximum - po.accepted_quantity))
        rejected = quantity - allowed
        po.accepted_quantity += allowed
        po.rejected_quantity += rejected
        if po.accepted_quantity >= po.quantity * .95 and received_on > po.due_date:
            po.status = "CLOSED"
        if rejected:
            self.debit_balances[po.vendor_id] = self.debit_balances.get(po.vendor_id, 0) + rejected * po.unit_price + rejected / po.quantity * po.freight
        return {"accepted": allowed, "rejected": rejected, "status": po.status}

    def match_invoice(self, invoice: Invoice) -> Invoice:
        # BR-07 and BR-10
        po = self.pos[invoice.po_id]
        reasons = []
        if invoice.quantity > po.accepted_quantity:
            reasons.append("QUANTITY_EXCEEDS_ACCEPTED_RECEIPT")
        tolerance = min(po.unit_price * .02, 100)
        if abs(invoice.unit_price - po.unit_price) > tolerance:
            reasons.append("UNIT_PRICE_OUTSIDE_TOLERANCE")
        if abs(invoice.total - po.computed_total) > 500:
            reasons.append("TOTAL_OUTSIDE_TOLERANCE")
        invoice.hold_reasons = reasons
        invoice.status = "HOLD" if reasons else "APPROVED"
        if not reasons:
            balance = self.debit_balances.get(invoice.vendor_id, 0)
            self.debit_balances[invoice.vendor_id] = max(0, balance - invoice.total)
            invoice.total -= min(balance, invoice.total)
            invoice.approved_on = invoice.received_on
        self.invoices[invoice.id] = invoice
        return invoice

    def payment_due(self, invoice: Invoice) -> date:
        # BR-08
        vendor = self.vendors[invoice.vendor_id]
        return invoice.received_on + timedelta(days=45 if vendor.msme else 30)

    def payment_amount(self, invoice: Invoice, paid_on: date, bank_rate: float = .065) -> float:
        # BR-08 and BR-09. Discounts apply to pre-GST value; this model has no GST field.
        days = (paid_on - (invoice.approved_on or invoice.received_on)).days
        amount = invoice.total * (.98 if days <= 10 else .99 if days <= 20 else 1)
        due = self.payment_due(invoice)
        if self.vendors[invoice.vendor_id].msme and paid_on > due:
            months = (paid_on - due).days / 30
            amount *= pow(1 + 3 * bank_rate / 12, months)
        return round(amount, 2)

    def payment_run(self, run_date: date, cash_limit: float = 2_500_000) -> list[dict]:
        # BR-11
        if run_date.weekday() not in (0, 3):
            raise ValueError("PAYMENT_RUN_MUST_BE_MONDAY_OR_THURSDAY")
        candidates = [i for i in self.invoices.values() if i.status == "APPROVED" and self.payment_due(i) <= run_date + timedelta(days=7)]
        candidates.sort(key=lambda i: (not self.vendors[i.vendor_id].msme, self.payment_due(i)))
        paid, total = [], 0.0
        for invoice in candidates:
            amount = self.payment_amount(invoice, run_date)
            if total + amount > cash_limit:
                continue
            paid.append({"invoice": invoice.id, "amount": amount, "due": self.payment_due(invoice).isoformat()})
            total += amount
            invoice.status = "PAID"
        return paid
