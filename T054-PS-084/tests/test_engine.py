from datetime import date, datetime

import pytest

from procurement.engine import ProcurementEngine
from procurement.models import Invoice, Item, PurchaseOrder, Quotation, Requisition, Vendor


def engine():
    e = ProcurementEngine({("KA", "MH"): 100}, {("USD", date(2026, 10, 1)): 80})
    e.register_item(Item("I1", "Bearing", 10))
    e.register_vendor(Vendor("V1", "KA", True, on_time_delivery_rate=96, quality_rejection_rate=2))
    e.register_vendor(Vendor("V2", "KA", False, on_time_delivery_rate=100, quality_rejection_rate=0))
    e.register_vendor(Vendor("V3", "KA", False, on_time_delivery_rate=80, quality_rejection_rate=10))
    return e


def quote(id, vendor, price, valid=date(2026, 11, 1)):
    return Quotation(id, vendor, "I1", 10, price, 0, "INR", datetime(2026, 10, 10, 9), valid)


def test_split_requisition_needs_director():
    e = engine()
    assert e.approve_requisition(Requisition("R1", "I1", 1, 260_000, date(2026, 10, 1))) == "MANAGER"
    assert e.approve_requisition(Requisition("R2", "I1", 1, 260_000, date(2026, 10, 7))) == "DIRECTOR"


def test_landed_cost_import_and_exchange_rate():
    e = engine()
    q = Quotation("Q", "V1", "I1", 2, 10, 0, "USD", datetime(2026, 10, 1), date(2026, 11, 1), True)
    assert e.landed_cost(q, "MH") == 1760
    q = Quotation("Q", "V1", "I1", 2, 10, 0, "USD", datetime(2026, 10, 2), date(2026, 11, 1), True)
    with pytest.raises(ValueError, match="MISSING_EXCHANGE_RATE"):
        e.landed_cost(q, "MH")


def test_award_scores_only_within_five_percent_and_manual_for_few_quotes():
    e = engine()
    result = e.award([quote("a", "V1", 100), quote("b", "V2", 103), quote("c", "V3", 120)], date(2026, 10, 15), "MH")
    assert result.vendor_id == "V1"  # V3's score cannot override 5% window.
    expensive = [quote("a", "V1", 20_000), quote("b", "V2", 21_000)]
    assert e.award(expensive, date(2026, 10, 15), "MH").status == "MANUAL_AWARD"


def test_receipt_exact_five_percent_and_debit_note():
    e = engine(); e.create_po(PurchaseOrder("P", "V1", "I1", 100, 10, 100, date(2026, 10, 10)))
    assert e.receive("P", 105, date(2026, 10, 11))["accepted"] == 105
    assert e.receive("P", 1, date(2026, 10, 11))["rejected"] == 1
    assert e.debit_balances["V1"] == 11


def test_invoice_price_tolerance_uses_lower_of_two_percent_or_100():
    e = engine(); e.create_po(PurchaseOrder("P", "V1", "I1", 10, 6000, 0, date(2026, 10, 10), accepted_quantity=10))
    held = e.match_invoice(Invoice("X", "V1", "P", 10, 6101, 60101, date(2026, 10, 11)))
    assert "UNIT_PRICE_OUTSIDE_TOLERANCE" in held.hold_reasons


def test_msme_interest_starts_after_day_45_and_payment_run_no_partial():
    e = engine(); e.create_po(PurchaseOrder("P", "V1", "I1", 1, 1_600_000, 0, date(2026, 10, 10), accepted_quantity=1))
    i1 = e.match_invoice(Invoice("X", "V1", "P", 1, 1_600_000, 1_600_000, date(2026, 1, 1)))
    assert e.payment_amount(i1, date(2026, 2, 15)) == 1_600_000
    assert e.payment_amount(i1, date(2026, 2, 16)) > 1_600_000
    e.create_po(PurchaseOrder("P2", "V2", "I1", 1, 1_600_000, 0, date(2026, 10, 10), accepted_quantity=1))
    e.match_invoice(Invoice("Y", "V2", "P2", 1, 1_600_000, 1_600_000, date(2026, 1, 1)))
    paid = e.payment_run(date(2026, 2, 16), 2_500_000)
    assert [p["invoice"] for p in paid] == ["X"]
