"""Validate the shared price contract and match devices by service date."""

import csv
import hashlib
import io
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

HEADER = (
    "device_id", "effective_from", "effective_to", "unit_price_cents",
    "currency", "price_source",
)


def iso_date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError(f"expected YYYY-MM-DD, got {value!r}")
    return parsed


@dataclass(frozen=True)
class Price:
    device_id: str
    start: date
    end: date | None
    cents: int
    source: str
    row: int

    def applies(self, on: date) -> bool:
        return self.start <= on and (self.end is None or on < self.end)


@dataclass(frozen=True)
class Catalog:
    by_device: dict[str, list[Price]]
    sha256: str

    def match(self, device_id: str, on: date) -> Price | None:
        return next((p for p in self.by_device.get(device_id, []) if p.applies(on)), None)


def load_catalog(path: Path) -> Catalog:
    raw = path.read_bytes()
    reader = csv.reader(io.StringIO(raw.decode("utf-8"), newline=""), strict=True)
    if tuple(next(reader, ())) != HEADER:
        raise ValueError(f"expected header {','.join(HEADER)}")

    by_device = defaultdict(list)
    for fields in reader:
        row = reader.line_num
        try:
            device, start, end, cents, currency, source = fields
            if not device or device.strip() != device or not source.strip():
                raise ValueError("device_id and price_source are required")
            if currency != "USD" or not re.fullmatch(r"[0-9]+", cents):
                raise ValueError("expected nonnegative integer USD cents per each")
            price = Price(device, iso_date(start), iso_date(end) if end else None,
                          int(cents), source, row)
            if price.end is not None and price.end <= price.start:
                raise ValueError("effective_to must follow effective_from")
        except ValueError as exc:
            raise ValueError(f"price CSV line {row}: {exc}") from exc
        by_device[device].append(price)

    for device, prices in by_device.items():
        prices.sort(key=lambda price: price.start)
        for previous, current in zip(prices, prices[1:]):
            if previous.end is None or current.start < previous.end:
                raise ValueError(
                    f"overlapping intervals for {device} on lines {previous.row} and {current.row}"
                )
    return Catalog(dict(by_device), hashlib.sha256(raw).hexdigest())
