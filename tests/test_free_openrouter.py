from copy import deepcopy

import pytest
from inspect_ai.model import GenerateConfig

from showcase_evals.free_openrouter import FreeOpenRouterAPI, validate_free_model

MODEL = "example/test:free"
CATALOG = {"data": [{"id": MODEL, "pricing": {"prompt": "0", "completion": "0"}}]}


@pytest.mark.parametrize("model", ["openrouter/free", "example/test", "example/missing:free"])
def test_paid_random_or_unknown_models_are_refused(model):
    with pytest.raises(ValueError):
        validate_free_model(model, CATALOG)


@pytest.mark.parametrize(
    "pricing",
    [
        {},
        {"prompt": "0"},
        {"prompt": "0", "completion": "0.0001"},
        {"prompt": "0", "completion": "NaN"},
        {"prompt": "0", "completion": "0", "request": "1"},
    ],
)
def test_missing_invalid_or_any_nonzero_price_is_refused(pricing):
    catalog = deepcopy(CATALOG)
    catalog["data"][0]["pricing"] = pricing
    with pytest.raises(ValueError):
        validate_free_model(MODEL, catalog)


def test_upstream_request_cannot_enable_paid_fallbacks(monkeypatch):
    monkeypatch.setattr("showcase_evals.free_openrouter.fetch_catalog", lambda: CATALOG)
    api = FreeOpenRouterAPI(MODEL, api_key="unit-test-placeholder")
    params = api.completion_params(GenerateConfig(max_tokens=100), tools=False)
    assert params["extra_body"]["provider"] == {
        "allow_fallbacks": False,
        "require_parameters": True,
        "max_price": {"prompt": 0, "completion": 0},
    }
    with pytest.raises(ValueError):
        api.completion_params(GenerateConfig(extra_body={"models": ["paid/model"]}), False)
    with pytest.raises(ValueError):
        api.completion_params(GenerateConfig(fallback_models=["openrouter/paid/model"]), False)


def test_alternate_credential_destination_is_refused():
    with pytest.raises(ValueError, match="only sends credentials"):
        FreeOpenRouterAPI(MODEL, base_url="https://example.com")
