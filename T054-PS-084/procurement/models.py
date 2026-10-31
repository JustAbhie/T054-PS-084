from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class Vendor:
    id: str
    state: str
    msme: bool
    payment_terms_days: int = 30
    on_time_delivery_rate: float = 0.0
    quality_rejection_rate: float = 0.0


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    weight_kg: float


@dataclass
class Requisition:
    id: str
    item_id: str
    quantity: float
    unit_price: float
    created_on: date
    approval: str = ""

    @property
    def value(self) -> float:
        return self.quantity * self.unit_price


@dataclass(frozen=True)
class Quotation:
    id: str
    vendor_id: str
    item_id: str
    quantity: float
    unit_price: float
    freight: float | None
    currency: str
    quoted_at: datetime
    valid_until: date
    imported: bool = False


@dataclass
class PurchaseOrder:
    id: str
    vendor_id: str
    item_id: str
    quantity: float
    unit_price: float
    freight: float
    due_date: date
    accepted_quantity: float = 0.0
    rejected_quantity: float = 0.0
    status: str = "OPEN"

    @property
    def computed_total(self) -> float:
        return self.quantity * self.unit_price + self.freight


@dataclass
class Invoice:
    id: str
    vendor_id: str
    po_id: str
    quantity: float
    unit_price: float
    total: float
    received_on: date
    approved_on: date | None = None
    status: str = "PENDING"
    hold_reasons: list[str] = field(default_factory=list)

