from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import ProcurementEngine
from .errors import ValidationError
from .io import as_date, dec, invoice, item, purchase_order, quote, requisition, vendor


def run_document(document: dict) -> dict:
    distances = {tuple(key.split("|")): dec(value) for key, value in document.get("distances_km", {}).items()}
    rates = {(key.split("|")[0], as_date(key.split("|")[1])): dec(value) for key, value in document.get("exchange_rates", {}).items()}
    engine = ProcurementEngine(document["buyer_state"], distances, rates)
    for record in document.get("vendors", []): engine.add_vendor(vendor(record))
    for record in document.get("items", []): engine.add_item(item(record))
    results: list[dict] = []
    for operation in document.get("operations", []):
        kind, data = operation["type"], operation["data"]
        if kind == "approve_requisition":
            value = requisition(data); results.append({"type": kind, "requisition_id": value.requisition_id, "status": engine.approve_requisition(value)})
        elif kind == "award":
            results.append({"type": kind, **engine.award([quote(q) for q in data["quotes"]], as_date(data["rfq_close"]))})
        elif kind == "create_po":
            value = purchase_order(data); engine.add_purchase_order(value); results.append({"type": kind, "po_id": value.po_id, "status": "CREATED"})
        elif kind == "receive_goods":
            results.append({"type": kind, **engine.receive_goods(data["po_id"], dec(data["quantity"]), as_date(data["received_on"]))})
        elif kind == "match_invoice":
            results.append({"type": kind, **engine.match_invoice(invoice(data))})
        elif kind == "payment_run":
            results.append({"type": kind, **engine.payment_run(as_date(data["run_date"]), dec(data.get("cash_limit", "2500000")))})
        else:
            raise ValidationError(f"UNKNOWN_OPERATION:{kind}")
    return {"results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="PS-084 file-driven procurement engine")
    parser.add_argument("input", type=Path, help="input JSON file")
    parser.add_argument("--output", type=Path, help="where to write results JSON")
    args = parser.parse_args()
    try:
        result = run_document(json.loads(args.input.read_text()))
    except (KeyError, ValueError, ValidationError) as error:
        parser.error(str(error))
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
