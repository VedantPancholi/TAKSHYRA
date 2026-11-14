import json

import pytest

from takshyra.local_ai import LocalAIConfig, call_ollama, evidence_cards, validate_output


def output(ref: str) -> str:
    return json.dumps({"hypotheses": [{
        "summary": "The observed freshness window may have been missed.",
        "category": "FRESHNESS_MISS", "confidence_label": "LOW",
        "supporting_evidence_refs": [ref], "contradicting_evidence_refs": [],
        "unknowns": ["The upstream cause is not verified."],
        "next_checks": ["CHECK_PIPELINE_SCHEDULE"],
    }]})


def test_model_output_is_advisory_and_cites_existing_evidence():
    ref = "incident:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    accepted = validate_output(output(ref), {ref})
    assert accepted[0]["status"] == "HYPOTHESIS"
    assert accepted[0]["next_checks"] == ["Inspect the pipeline schedule and latest upstream completion."]
    with pytest.raises(ValueError, match="missing"):
        validate_output(output(ref), set())
    invented = json.loads(output(ref))
    invented["hypotheses"][0]["status"] = "CONFIRMED"
    with pytest.raises(ValueError, match="schema"):
        validate_output(json.dumps(invented), {ref})
    invented["hypotheses"][0].pop("status")
    invented["hypotheses"][0]["next_checks"] = ["DELETE_PRODUCTION_DATA"]
    with pytest.raises(ValueError, match="schema"):
        validate_output(json.dumps(invented), {ref})


def test_model_receives_only_bounded_safe_evidence_cards():
    snapshot = {
        "incident_id": "i", "category": "QUALITY_FAILURE", "error_code": "QUALITY_ROW_COUNT",
        "provenance": "simulated", "run": {"id": "r", "status": "SUCCEEDED",
        "error_code": None, "quality_status": "FAIL"},
        "checks": [{"id": "q", "rule_id": "row_count_ratio", "outcome": "FAIL",
                    "observed": "sensitive row content", "expected": "secret"}],
    }
    cards, refs = evidence_cards(snapshot)
    assert refs == {"incident:i", "run:r", "check:q"}
    assert "sensitive" not in json.dumps(cards)
    assert "secret" not in json.dumps(cards)


def test_ollama_opt_in_rejects_remote_targets(monkeypatch):
    monkeypatch.setenv("TAKSHYRA_DIAGNOSIS_PROVIDER", "rules")
    assert not LocalAIConfig.from_env().enabled
    monkeypatch.setenv("TAKSHYRA_DIAGNOSIS_PROVIDER", "ollama")
    monkeypatch.setenv("TAKSHYRA_OLLAMA_MODEL", "small-local-model")
    monkeypatch.setenv("TAKSHYRA_OLLAMA_BASE_URL", "http://example.com:11434")
    with pytest.raises(ValueError, match="local"):
        LocalAIConfig.from_env()
    monkeypatch.setenv("TAKSHYRA_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    assert LocalAIConfig.from_env().endpoint == "http://127.0.0.1:11434/api/generate"


def test_ollama_request_uses_structured_nonstreaming_local_api(monkeypatch):
    ref = "incident:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, limit):
            assert limit == 16385
            return json.dumps({"done": True, "response": output(ref)}).encode()

    class Opener:
        def open(self, request, timeout):
            seen["request"] = request
            seen["timeout"] = timeout
            return Response()

    monkeypatch.setattr("takshyra.local_ai.build_opener", lambda *_args: Opener())
    config = LocalAIConfig(True, "local-model", "http://127.0.0.1:11434/api/generate")
    assert call_ollama(config, [{"ref": ref}]) == output(ref)
    request = seen["request"]
    payload = json.loads(request.data)
    assert request.full_url == config.endpoint
    assert seen["timeout"] == 8.0
    assert payload["stream"] is False
    assert payload["format"]["type"] == "object"
    assert payload["options"]["num_predict"] == 384
