"""Opted-in ADF sandbox poll and local incident ingestion; no Azure mutations."""

import json
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.adf import AdfObserver, AdfScope, live_transport
from takshyra.adf_ingestion import ingest_runs, register_binding
from takshyra.db import engine
from takshyra.models import Tenant


def main() -> None:
    if os.getenv("ENABLE_LIVE_AZURE_TESTS") != "true":
        raise SystemExit("Live Azure ingestion disabled; set ENABLE_LIVE_AZURE_TESTS=true explicitly")
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError:
        raise SystemExit("Install optional azure-identity in the execution environment first") from None

    tenant_slug = os.environ["TAKSHYRA_TENANT_SLUG"]
    local_name = os.environ["TAKSHYRA_ADF_LOCAL_PIPELINE"]
    external_name = os.environ["AZURE_ADF_PIPELINE_NAME"]
    with Session(engine()) as db:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == tenant_slug))
        if tenant is None:
            raise SystemExit("Unknown local tenant")
        scope = AdfScope(
            tenant_id=tenant.id,
            subscription_id=os.environ["AZURE_ADF_SUBSCRIPTION_ID"],
            resource_group=os.environ["AZURE_ADF_RESOURCE_GROUP"],
            factory_name=os.environ["AZURE_ADF_FACTORY_NAME"],
        )
        credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
        try:
            observer = AdfObserver(
                tenant_id=scope.tenant_id, allowed_targets=frozenset({scope.target}),
                transport=live_transport(
                    lambda: credential.get_token("https://management.azure.com/.default").token,
                ),
            )
            until = datetime.now(timezone.utc)
            result = observer.query(scope, until - timedelta(hours=1), until, limit=100)
        finally:
            credential.close()
        if result["truncated"]:
            raise SystemExit("ADF result was truncated; narrow the window before ingesting")
        binding = register_binding(
            db, scope=scope, local_name=local_name, external_name=external_name,
        )
        counts = ingest_runs(db, scope=scope, binding=binding, result=result)
        db.commit()
        print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
