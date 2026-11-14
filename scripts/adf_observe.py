"""Explicitly opted-in, read-only ADF sandbox query. No persistent credentials."""

import json
import os
from datetime import datetime, timedelta, timezone

from takshyra.adf import AdfObserver, AdfScope, live_transport


def main() -> None:
    if os.getenv("ENABLE_LIVE_AZURE_TESTS") != "true":
        raise SystemExit("Live Azure observation disabled; set ENABLE_LIVE_AZURE_TESTS=true explicitly")
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError:
        raise SystemExit("Install optional azure-identity in the local environment first") from None
    scope = AdfScope(
        tenant_id=os.environ["TAKSHYRA_TENANT_SLUG"],
        subscription_id=os.environ["AZURE_ADF_SUBSCRIPTION_ID"],
        resource_group=os.environ["AZURE_ADF_RESOURCE_GROUP"],
        factory_name=os.environ["AZURE_ADF_FACTORY_NAME"],
    )
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    try:
        observer = AdfObserver(
            tenant_id=scope.tenant_id, allowed_targets=frozenset({scope.target}),
            transport=live_transport(lambda: credential.get_token("https://management.azure.com/.default").token),
        )
        until = datetime.now(timezone.utc)
        result = observer.query(scope, until - timedelta(hours=1), until, limit=25)
        print(json.dumps(result, sort_keys=True))
    finally:
        credential.close()


if __name__ == "__main__":
    main()
