from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from .models import Invoice, Item, PurchaseOrder, Quote, Requisition, Vendor


def dec(value: object) -> Decimal:
    return Decimal(str(value))


def as_date(value: str) -> date:
    return date.fromisoformat(value)


def vendor(data: dict) -> Vendor:
    return Vendor(data["vendor_id"], data["state"], bool(data["is_msme"]), dec(data["on_time_delivery_pct"]), dec(data["rejection_pct"]))


def item(data: dict) -> Item:
    return Item(data["item_id"], data["description"], dec(data["weight_kg"]))


def requisition(data: dict) -> Requisition:
    return Requisition(data["requisition_id"], data["item_id"], dec(data["quantity"]), dec(data["unit_price"]), as_date(data["requested_on"]))


def quote(data: dict) -> Quote:
    freight = data.get("freight")
    return Quote(data["quote_id"], data["rfq_id"], data["vendor_id"], data["item_id"], dec(data["quantity"]), dec(data["unit_price"]), data["currency"], datetime.fromisoformat(data["quoted_at"]), as_date(data["valid_until"]), dec(freight) if freight is not None else None, bool(data.get("is_import", False)))


def purchase_order(data: dict) -> PurchaseOrder:
    return PurchaseOrder(data["po_id"], data["vendor_id"], data["item_id"], dec(data["quantity"]), dec(data["unit_price"]), dec(data["freight"]), as_date(data["due_date"]))


def invoice(data: dict) -> Invoice:
    return Invoice(data["invoice_id"], data["po_id"], data["vendor_id"], dec(data["quantity"]), dec(data["unit_price"]), dec(data["total"]), as_date(data["received_on"]))
