"""A narrowly scoped Inspect adapter that refuses paid OpenRouter routes."""

from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from inspect_ai.model import GenerateConfig, modelapi
from inspect_ai.model._providers.openrouter import OpenRouterAPI

CATALOG_URL = "https://openrouter.ai/api/v1/models"
BASE_URL = "https://openrouter.ai/api/v1"


def validate_free_model(model_name: str, catalog: dict[str, Any]) -> dict[str, Any]:
    """Fail closed on an unknown route, missing prices, or any nonzero price."""
    if not model_name.endswith(":free"):
        raise ValueError("OpenRouter requests must use an explicit :free model ID")
    matches = [entry for entry in catalog.get("data", []) if entry.get("id") == model_name]
    if len(matches) != 1:
        raise ValueError("Free model is missing or ambiguous in the current OpenRouter catalog")
    entry = matches[0]
    pricing = entry.get("pricing")
    if not isinstance(pricing, dict) or not {"prompt", "completion"} <= pricing.keys():
        raise ValueError("A free route must advertise both input and output prices")
    try:
        zero = all(
            Decimal(str(price)).is_finite() and Decimal(str(price)) == 0
            for price in pricing.values()
        )
    except (InvalidOperation, TypeError, ValueError):
        zero = False
    if not zero:
        raise ValueError("OpenRouter route advertises nonzero or unparseable pricing")
    return entry


def fetch_catalog() -> dict[str, Any]:
    response = httpx.get(CATALOG_URL, timeout=20, follow_redirects=False)
    response.raise_for_status()
    return response.json()


class FreeOpenRouterAPI(OpenRouterAPI):
    """Use the native adapter while enforcing the study's zero-price contract.

    The catalog check happens during setup, outside timed generations. The
    upstream zero-price routing ceiling applies to every inference request.
    This adapter is version-pinned because it extends Inspect's provider class.
    """

    def __init__(
        self,
        model_name: str,
        base_url=None,
        api_key=None,
        config: GenerateConfig | None = None,
        **model_args: Any,
    ):
        if base_url is not None and base_url.rstrip("/") != BASE_URL:
            raise ValueError("The free adapter only sends credentials to OpenRouter")
        if any(key in model_args for key in ("models", "provider", "transforms")):
            raise ValueError("Routing overrides and model fallback lists are forbidden")
        self.catalog_entry = validate_free_model(model_name, fetch_catalog())
        model_args.setdefault("max_retries", 0)
        super().__init__(
            model_name,
            base_url=BASE_URL,
            api_key=api_key,
            config=config or GenerateConfig(),
            **model_args,
        )

    def completion_params(self, config: GenerateConfig, tools: bool) -> dict[str, Any]:
        if config.fallback_models or config.extra_body:
            raise ValueError("Fallbacks and extra request bodies are forbidden for free-only runs")
        if self.models or self.transforms:
            raise ValueError("Routing transformations and model fallbacks are forbidden")
        params = super().completion_params(config, tools)
        body = params.setdefault("extra_body", {})
        body["provider"] = {
            "allow_fallbacks": False,
            "require_parameters": True,
            "max_price": {"prompt": 0, "completion": 0},
        }
        return params


free_openrouter = modelapi("free_openrouter")(FreeOpenRouterAPI)
