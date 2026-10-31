from datetime import date, datetime
from decimal import Decimal
import unittest

from p2p_engine.engine import ProcurementEngine
from p2p_engine.errors import ValidationError
from p2p_engine.models import Invoice, Item, PurchaseOrder, Quote, Requisition, Vendor


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.e = ProcurementEngine("MH", {("KA", "MH"): Decimal("100")}, {("USD", date(2026, 10, 1)): Decimal("80")})
        self.e.add_item(Item("I", "Item", Decimal("10")))
        self.e.add_vendor(Vendor("A", "KA", True, Decimal("96"), Decimal("2")))
        self.e.add_vendor(Vendor("B", "KA", False, Decimal("100"), Decimal("0")))
        self.e.add_vendor(Vendor("C", "KA", False, Decimal("80"), Decimal("10")))

    def q(self, quote_id, vendor, price, valid="2026-11-01"):
        return Quote(quote_id, "R", vendor, "I", Decimal("10"), Decimal(str(price)), "INR", datetime(2026, 10, 10, 9), date.fromisoformat(valid), Decimal("0"))

    def po(self, id="P", vendor="A", price="100", quantity="100"):
        value = PurchaseOrder(id, vendor, "I", Decimal(quantity), Decimal(price), Decimal("100"), date(2026, 10, 10))
        self.e.add_purchase_order(value); return value

    def test_br01_split_requisition_uses_combined_value(self):
        self.assertEqual(self.e.approve_requisition(Requisition("R1", "I", Decimal("1"), Decimal("260000"), date(2026, 10, 1))), "MANAGER_REQUIRED")
        self.assertEqual(self.e.approve_requisition(Requisition("R2", "I", Decimal("1"), Decimal("260000"), date(2026, 10, 7))), "DIRECTOR_REQUIRED")

    def test_br02_import_cost_and_missing_exchange_rate(self):
        quote = Quote("Q", "R", "A", "I", Decimal("2"), Decimal("10"), "USD", datetime(2026, 10, 1, 8), date(2026, 11, 1), Decimal("0"), True)
        self.assertEqual(self.e.landed_cost(quote), Decimal("1760.00"))
        missing = Quote("Q2", "R", "A", "I", Decimal("2"), Decimal("10"), "USD", datetime(2026, 10, 2, 8), date(2026, 11, 1), Decimal("0"), True)
        with self.assertRaisesRegex(ValidationError, "MISSING_EXCHANGE_RATE"): self.e.landed_cost(missing)

    def test_br04_score_cannot_beat_five_percent_window(self):
        result = self.e.award([self.q("1", "A", 100), self.q("2", "B", 103), self.q("3", "C", 120)], date(2026, 10, 15))
        self.assertEqual(result["winner"], "A")

    def test_br05_fewer_than_three_large_quotes_is_manual_award(self):
        result = self.e.award([self.q("1", "A", 20000), self.q("2", "B", 21000)], date(2026, 10, 15))
        self.assertEqual(result["status"], "MANUAL_AWARD")

    def test_br06_exact_five_percent_is_accepted_and_more_is_rejected(self):
        self.po(); self.assertEqual(self.e.receive_goods("P", Decimal("105"), date(2026, 10, 11))["accepted"], "105")
        result = self.e.receive_goods("P", Decimal("1"), date(2026, 10, 11))
        self.assertEqual(result["rejected"], "1"); self.assertEqual(result["debit_note"], "101.00")

    def test_br07_lower_of_two_percent_or_100_is_used(self):
        self.po(price="6000", quantity="10"); self.e.receive_goods("P", Decimal("10"), date(2026, 10, 11))
        result = self.e.match_invoice(Invoice("X", "P", "A", Decimal("10"), Decimal("6101"), Decimal("60110"), date(2026, 10, 11)))
        self.assertIn("UNIT_PRICE_OUTSIDE_TOLERANCE", result["hold_reasons"])

    def test_br08_msme_interest_starts_on_day_46(self):
        self.po(price="1000", quantity="1"); self.e.receive_goods("P", Decimal("1"), date(2026, 1, 1))
        inv = Invoice("X", "P", "A", Decimal("1"), Decimal("1000"), Decimal("1100"), date(2026, 1, 1)); self.e.match_invoice(inv)
        self.assertEqual(self.e.payment_amount(inv, date(2026, 2, 15)), Decimal("1100.00"))
        self.assertGreater(self.e.payment_amount(inv, date(2026, 2, 16)), Decimal("1100.00"))

    def test_br09_discount_windows(self):
        self.po(price="100", quantity="1"); self.e.receive_goods("P", Decimal("1"), date(2026, 1, 1))
        inv = Invoice("X", "P", "A", Decimal("1"), Decimal("100"), Decimal("200"), date(2026, 1, 1)); self.e.match_invoice(inv)
        self.assertEqual(self.e.payment_amount(inv, date(2026, 1, 11)), Decimal("196.00"))
        self.assertEqual(self.e.payment_amount(inv, date(2026, 1, 21)), Decimal("198.00"))

    def test_br10_debit_note_carries_remainder(self):
        self.po(); self.e.receive_goods("P", Decimal("106"), date(2026, 10, 11))
        self.assertEqual(self.e.debit_balances["A"], Decimal("101.00"))

    def test_br11_only_monday_thursday_and_no_partial_payments(self):
        self.po("P1", "A", "1600000", "1"); self.e.receive_goods("P1", Decimal("1"), date(2026, 1, 1))
        self.e.match_invoice(Invoice("A1", "P1", "A", Decimal("1"), Decimal("1600000"), Decimal("1600100"), date(2026, 1, 1)))
        self.po("P2", "B", "1600000", "1"); self.e.receive_goods("P2", Decimal("1"), date(2026, 1, 1))
        self.e.match_invoice(Invoice("B1", "P2", "B", Decimal("1"), Decimal("1600000"), Decimal("1600100"), date(2026, 1, 1)))
        with self.assertRaisesRegex(ValidationError, "MONDAY_OR_THURSDAY"): self.e.payment_run(date(2026, 2, 17))
        paid = self.e.payment_run(date(2026, 2, 16))["payments"]
        self.assertEqual([row["invoice_id"] for row in paid], ["A1"])


if __name__ == "__main__": unittest.main()
