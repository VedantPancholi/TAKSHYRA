"""Fixed declarative orders contract; no user-supplied expressions are executed."""

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FieldRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    type: Literal["string", "timestamp", "decimal"] = "string"
    required: bool = True


class OrdersContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_fields: tuple[FieldRule, ...] = Field(min_length=4, max_length=16)
    allow_extra_fields: bool = False
    expected_row_count: int | None = Field(default=4, ge=1, le=100_000)
    min_row_ratio: float = Field(default=0.95, gt=0, le=1)
    max_customer_null_rate: float | int = Field(default=0, ge=0, le=1)
    max_duplicate_rate: float | int = Field(default=0, ge=0, le=1)
    max_age_hours: int | None = Field(default=None, ge=1, le=8760)

    @model_validator(mode="after")
    def fixed_orders_fields(self):
        names = [field.name for field in self.schema_fields]
        core = {"order_id": "string", "order_ts": "timestamp", "amount": "decimal", "customer_id": "string"}
        by_name = {field.name: field for field in self.schema_fields}
        if len(names) != len(set(names)) or any(
            name not in by_name or by_name[name].type != kind or not by_name[name].required
            for name, kind in core.items()
        ):
            raise ValueError("Orders contract must retain each required core field and type")
        return self


SEED_CONTRACT = OrdersContract(schema_fields=(
    FieldRule(name="order_id"), FieldRule(name="order_ts", type="timestamp"),
    FieldRule(name="amount", type="decimal"), FieldRule(name="customer_id"),
))


def canonical(contract: OrdersContract) -> tuple[str, str]:
    value = json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return value, hashlib.sha256(value.encode()).hexdigest()


def evaluate(contract: OrdersContract, rows: list[dict], source_fields: list[str], clock: datetime | None = None) -> list[dict]:
    checks = []

    def add(rule_id: str, outcome: str, expected: str, observed: str):
        checks.append({"rule_id": rule_id, "outcome": outcome, "expected": expected, "observed": observed})

    required = {field.name for field in contract.schema_fields if field.required}
    allowed = {field.name for field in contract.schema_fields}
    missing = sorted(required - set(source_fields))
    extra = sorted(set(source_fields) - allowed)
    schema_ok = not missing and (contract.allow_extra_fields or not extra)
    add("schema", "PASS" if schema_ok else "FAIL", "required fields present; extras by policy",
        f"missing={','.join(missing)};extra={','.join(extra)}")
    invalid = 0
    for row in rows:
        for field in contract.schema_fields:
            value = row.get(field.name)
            if not value:
                if field.required:
                    invalid += 1
                continue
            if field.type == "timestamp":
                try:
                    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        invalid += 1
                except ValueError:
                    invalid += 1
            elif field.type == "decimal":
                try:
                    if not Decimal(value).is_finite():
                        invalid += 1
                except InvalidOperation:
                    invalid += 1
    add("schema_types", "PASS" if invalid == 0 else "FAIL", "0 invalid required or typed values", str(invalid))

    if contract.expected_row_count is None:
        add("row_count_ratio", "UNKNOWN", "baseline available", str(len(rows)))
    else:
        ratio = len(rows) / contract.expected_row_count
        add("row_count_ratio", "PASS" if ratio >= contract.min_row_ratio else "FAIL",
            f">={contract.min_row_ratio} of {contract.expected_row_count}", f"{len(rows)}/{contract.expected_row_count}")

    if not rows:
        add("customer_null_rate", "UNKNOWN", f"<={contract.max_customer_null_rate}", "empty")
        add("order_id_duplicate_rate", "UNKNOWN", f"<={contract.max_duplicate_rate}", "empty")
    else:
        nulls = sum(not row.get("customer_id") for row in rows)
        keys = [row.get("order_id") for row in rows]
        duplicates = len(keys) - len(set(keys))
        add("customer_null_rate", "PASS" if nulls / len(rows) <= contract.max_customer_null_rate else "FAIL",
            f"<={contract.max_customer_null_rate}", f"{nulls}/{len(rows)}")
        add("order_id_duplicate_rate", "PASS" if None not in keys and duplicates / len(rows) <= contract.max_duplicate_rate else "FAIL",
            f"<={contract.max_duplicate_rate}", f"{duplicates}/{len(rows)};null_keys={keys.count(None)}")

    if contract.max_age_hours is not None:
        timestamps = []
        for row in rows:
            try:
                value = datetime.fromisoformat(row["order_ts"].replace("Z", "+00:00"))
                if value.tzinfo is None:
                    raise ValueError("timezone missing")
                timestamps.append(value.astimezone(timezone.utc))
            except (KeyError, AttributeError, ValueError):
                timestamps = []
                break
        latest = max(timestamps) if timestamps else None
        age = ((clock or datetime.now(timezone.utc)) - latest).total_seconds() / 3600 if latest else None
        add("freshness", "UNKNOWN" if age is None else ("PASS" if age <= contract.max_age_hours else "FAIL"),
            f"<={contract.max_age_hours}h", "unavailable" if age is None else f"{age:.2f}h")
    return checks


def decision(checks: list[dict]) -> tuple[str, str]:
    outcomes = {check["outcome"] for check in checks}
    if "FAIL" in outcomes:
        return "FAIL", "QUARANTINED"
    if "UNKNOWN" in outcomes:
        return "UNKNOWN", "HELD"
    return "PASS", "PUBLISHED"
