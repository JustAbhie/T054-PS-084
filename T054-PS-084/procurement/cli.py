from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from .engine import ProcurementEngine
from .models import Item, Quotation, Vendor


def run_demo(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text())
    engine = ProcurementEngine({tuple(k.split("|")): v for k, v in data["distances"].items()})
    for value in data["vendors"]:
        engine.register_vendor(Vendor(**value))
    for value in data["items"]:
        engine.register_item(Item(**value))
    quotes = [Quotation(**{**q, "quoted_at": datetime.fromisoformat(q["quoted_at"]), "valid_until": date.fromisoformat(q["valid_until"])}) for q in data["quotes"]]
    award = engine.award(quotes, date.fromisoformat(data["rfq_close"]), data["buyer_state"])
    result = [{"event": "award", **award.__dict__}]
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PS-084 procurement engine")
    parser.add_argument("input", help="JSON demo input")
    run_demo(parser.parse_args().input)
