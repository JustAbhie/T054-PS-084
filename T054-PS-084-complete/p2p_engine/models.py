from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Vendor:
    vendor_id: str
    state: str
    is_msme: bool
    on_time_delivery_pct: Decimal
    rejection_pct: Decimal


@dataclass(frozen=True)
class Item:
    item_id: str
    description: str
    weight_kg: Decimal


@dataclass
class Requisition:
    requisition_id: str
    item_id: str
    quantity: Decimal
    unit_price: Decimal
    requested_on: date
    approval_status: str = "PENDING"

    @property
    def value(self) -> Decimal:
        return self.quantity * self.unit_price


@dataclass(frozen=True)
class Quote:
    quote_id: str
    rfq_id: str
    vendor_id: str
    item_id: str
    quantity: Decimal
    unit_price: Decimal
    currency: str
    quoted_at: datetime
    valid_until: date
    freight: Decimal | None = None
    is_import: bool = False


@dataclass
class PurchaseOrder:
    po_id: str
    vendor_id: str
    item_id: str
    quantity: Decimal
    unit_price: Decimal
    freight: Decimal
    due_date: date
    accepted_quantity: Decimal = Decimal("0")
    rejected_quantity: Decimal = Decimal("0")
    status: str = "OPEN"

    @property
    def expected_total(self) -> Decimal:
        return self.quantity * self.unit_price + self.freight


@dataclass
class Invoice:
    invoice_id: str
    po_id: str
    vendor_id: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    received_on: date
    status: str = "PENDING"
    approved_on: date | None = None
    hold_reasons: list[str] = field(default_factory=list)
    debit_applied: Decimal = Decimal("0")
