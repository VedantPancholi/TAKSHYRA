"""Bounded, read-only Azure Data Factory pipeline-run observer."""

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable
from urllib.request import HTTPRedirectHandler, Request, build_opener

API_VERSION = "2018-06-01"
STATUS = {"Queued", "InProgress", "Succeeded", "Failed", "Canceling", "Cancelled"}
Transport = Callable[[str, dict], dict]


@dataclass(frozen=True)
class AdfScope:
    tenant_id: str
    subscription_id: str
    resource_group: str
    factory_name: str

    def __post_init__(self) -> None:
        uuid.UUID(self.subscription_id)
        if not re.fullmatch(r"[A-Za-z0-9_.()-]{1,90}", self.resource_group):
            raise ValueError("Invalid resource group")
        if not re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", self.factory_name) or len(self.factory_name) > 63:
            raise ValueError("Invalid factory name")
        if not self.tenant_id:
            raise ValueError("Tenant required")

    @property
    def target(self) -> str:
        return f"{self.subscription_id.lower()}/{self.resource_group.lower()}/{self.factory_name.lower()}"

    @property
    def url(self) -> str:
        return (f"https://management.azure.com/subscriptions/{self.subscription_id}"
                f"/resourceGroups/{self.resource_group}/providers/Microsoft.DataFactory"
                f"/factories/{self.factory_name}/queryPipelineRuns?api-version={API_VERSION}")


class AdfObserver:
    def __init__(self, *, tenant_id: str, allowed_targets: frozenset[str], transport: Transport):
        self.tenant_id = tenant_id
        self.allowed_targets = allowed_targets
        self.transport = transport

    def query(self, scope: AdfScope, since: datetime, until: datetime, *, limit: int = 100) -> dict:
        if scope.tenant_id != self.tenant_id or scope.target not in self.allowed_targets:
            raise PermissionError("Factory outside tenant allowlist")
        if (since.tzinfo is None or until.tzinfo is None or
                not timedelta(0) < until - since <= timedelta(hours=24)):
            raise ValueError("Query window must be timezone-aware and at most 24 hours")
        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")
        body = {"lastUpdatedAfter": since.isoformat(), "lastUpdatedBefore": until.isoformat()}
        seen_tokens: set[str] = set()
        items: list[dict] = []
        pages = 0
        next_token: str | None = None
        more_in_page = False
        while pages < 3 and len(items) < limit:
            if next_token:
                body["continuationToken"] = next_token
            page = self.transport(scope.url, body.copy())
            pages += 1
            if not isinstance(page, dict) or not isinstance(page.get("value"), list):
                raise ValueError("Invalid ADF response")
            more_in_page = len(page["value"]) > limit - len(items)
            for run in page["value"]:
                if len(items) >= limit:
                    break
                if not isinstance(run, dict):
                    raise ValueError("Invalid ADF run")
                run_id = run.get("runId")
                pipeline = run.get("pipelineName")
                status = run.get("status")
                if not (isinstance(run_id, str) and len(run_id) <= 128 and
                        isinstance(pipeline, str) and len(pipeline) <= 128 and status in STATUS):
                    raise ValueError("Invalid ADF run fields")
                items.append({
                    "source": "azure_adf", "tenant_id": self.tenant_id,
                    "factory": scope.target, "run_id": run_id,
                    "pipeline_name": pipeline, "status": status,
                    "run_start": run.get("runStart") if isinstance(run.get("runStart"), str) else None,
                    "run_end": run.get("runEnd") if isinstance(run.get("runEnd"), str) else None,
                })
            token = page.get("continuationToken")
            if token is None:
                next_token = None
                break
            if not isinstance(token, str) or not token or len(token) > 2048 or token in seen_tokens:
                raise ValueError("Invalid ADF continuation token")
            seen_tokens.add(token)
            next_token = token
        return {"items": items, "truncated": next_token is not None or more_in_page, "pages": pages}


def live_transport(token_provider: Callable[[], str]) -> Transport:
    """Only the explicit live script supplies a credential; never logs response bodies."""
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            return None

    opener = build_opener(NoRedirect)

    def send(url: str, body: dict) -> dict:
        if not url.startswith("https://management.azure.com/subscriptions/"):
            raise ValueError("Unexpected Azure host")
        request = Request(url, data=json.dumps(body).encode(), method="POST", headers={
            "Authorization": f"Bearer {token_provider()}", "Content-Type": "application/json",
        })
        with opener.open(request, timeout=8) as response:
            payload = response.read(1_000_001)
        if len(payload) > 1_000_000:
            raise ValueError("ADF response too large")
        return json.loads(payload)
    return send
