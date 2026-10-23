import csv
import hashlib
import json
import os
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from takshyra.contracts import SEED_CONTRACT, OrdersContract, canonical, decision, evaluate


def artifact_paths(output_root: str, tenant_id: str, run_id: str) -> tuple[Path, Path]:
    # Both identifiers are server-generated UUIDs; refuse legacy/corrupt path values.
    import uuid

    uuid.UUID(tenant_id)
    uuid.UUID(run_id)
    directory = Path(output_root).resolve() / tenant_id / run_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "orders.parquet", directory / "manifest.json"


def read_manifest(output_root: str, tenant_id: str, run_id: str) -> dict | None:
    parquet, manifest = artifact_paths(output_root, tenant_id, run_id)
    if not manifest.is_file() or not parquet.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        checksum = hashlib.sha256(parquet.read_bytes()).hexdigest()
        if data.get("sha256") != checksum or data.get("run_id") != run_id:
            return None
        if pq.read_metadata(parquet).num_rows != data.get("row_count"):
            return None
        return data
    except (ValueError, OSError, pa.ArrowException):
        return None


def transform(fixture_path: str, output_root: str, tenant_id: str, run_id: str, *,
              drop_last_row: bool = False, contract: OrdersContract = SEED_CONTRACT,
              contract_version: int = 1) -> dict:
    _, definition_hash = canonical(contract)
    source = Path(fixture_path).resolve()
    if not source.is_file() or source.stat().st_size > 10_000_000:
        raise ValueError("SOURCE_UNAVAILABLE_OR_TOO_LARGE")
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        source_fields = reader.fieldnames or []
        if not source_fields or len(source_fields) != len(set(source_fields)):
            raise ValueError("SOURCE_SCHEMA_INVALID")
        rows = list(reader)
    if len(rows) > 100_000:
        raise ValueError("SOURCE_ROW_LIMIT")
    source_row_count = len(rows)
    if drop_last_row and rows:
        rows = rows[:-1]
    checks = evaluate(contract, rows, source_fields)
    checks.append({"rule_id": "source_row_count_match", "outcome": "PASS" if len(rows) == source_row_count else "FAIL",
                   "expected": str(source_row_count), "observed": str(len(rows))})
    quality_status, publication_status = decision(checks)
    existing = read_manifest(output_root, tenant_id, run_id)
    if existing:
        parquet, _ = artifact_paths(output_root, tenant_id, run_id)
        if (existing.get("contract_hash") != definition_hash or existing.get("contract_version") != contract_version
                or existing.get("schema_fields") != source_fields or existing.get("checks") != checks
                or existing.get("quality_status") != quality_status
                or existing.get("publication_status") != publication_status
                or pq.read_table(parquet).to_pylist() != rows):
            raise ValueError("CONTRACT_MANIFEST_MISMATCH")
        return existing
    table = pa.Table.from_pylist(rows, schema=pa.schema([(name, pa.string()) for name in source_fields]))
    parquet, manifest = artifact_paths(output_root, tenant_id, run_id)
    staged = parquet.with_suffix(".staging")
    pq.write_table(table, staged)
    if pq.read_metadata(staged).num_rows != len(rows):
        staged.unlink(missing_ok=True)
        raise ValueError("PARQUET_ROW_MISMATCH")
    os.replace(staged, parquet)
    data = {
        "run_id": run_id,
        "row_count": len(rows),
        "sha256": hashlib.sha256(parquet.read_bytes()).hexdigest(),
        "contract_version": contract_version,
        "contract_hash": definition_hash,
        "schema_fields": source_fields,
        "quality_status": quality_status,
        "publication_status": publication_status,
        "checks": checks,
    }
    staged_manifest = manifest.with_suffix(".staging")
    staged_manifest.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    os.replace(staged_manifest, manifest)
    return data
