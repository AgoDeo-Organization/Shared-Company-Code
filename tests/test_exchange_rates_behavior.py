"""Unit tests for exchange rate getters."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from julien_python_toolkit import exchange_rates


class _FakeResponse:
    """Simple response object used to mock HTTP calls."""

    def __init__(self, status_code: int, payload: object, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> object:
        """Return mocked payload or raise it when payload is an exception."""

        if isinstance(self._payload, Exception):
            raise self._payload

        return self._payload



def _build_getter(tmp_path: Path) -> exchange_rates.OpenExchangeRateGetterWithCache:
    """Create an exchange rate getter wired to temporary files."""

    cache_path = tmp_path / "exchange_rate_cache.json"

    return exchange_rates.OpenExchangeRateGetterWithCache(
        api_key="my-secret-key",
        path_to_cache=str(cache_path),
    )



def test_exchange_rate_getter_requires_subclass_implementation() -> None:
    """Base getter should raise when method is not implemented."""

    getter = exchange_rates.ExchangeRateGetter()

    with pytest.raises(NotImplementedError):
        getter.get_exchange_rate(datetime.date.today(), "USD", "EUR")



def test_simple_exchange_rate_getter_always_returns_unity() -> None:
    """Simple getter should return 1.0 for any input."""

    getter = exchange_rates.SimpleExchangeRateGetter()

    result = getter.get_exchange_rate(datetime.date(2024, 1, 1), "EUR", "JPY")

    assert result == 1.0



def test_init_raises_for_missing_api_key(tmp_path: Path) -> None:
    """Getter init should fail when API key is missing."""

    with pytest.raises(ValueError, match="API key is required"):
        exchange_rates.OpenExchangeRateGetterWithCache(
            api_key="",
            path_to_cache=str(tmp_path / "cache.json"),
        )



def test_init_loads_api_key_and_existing_cache(tmp_path: Path) -> None:
    """Init should trim API key input and load existing JSON cache."""

    cache_path = tmp_path / "exchange_rate_cache.json"

    cache_payload = {"2024-01-01_USD_EUR": 0.9}
    cache_path.write_text(json.dumps(cache_payload), encoding="utf-8")

    getter = exchange_rates.OpenExchangeRateGetterWithCache(
        api_key=" my-key-with-spaces \n",
        path_to_cache=str(cache_path),
    )

    assert getter.api_key == "my-key-with-spaces"
    assert getter.cache == cache_payload



def test_load_cache_returns_empty_when_cache_does_not_exist(tmp_path: Path) -> None:
    """Init should create an empty in-memory cache if file is absent."""

    getter = _build_getter(tmp_path)

    assert getter.cache == {}



def test_save_cache_persists_data(tmp_path: Path) -> None:
    """save_cache should write in-memory cache data to disk."""

    getter = _build_getter(tmp_path)
    getter.cache = {"2024-03-03_USD_CAD": 1.4}

    getter._save_cache()

    saved_data = json.loads(Path(getter.path_to_cache).read_text(encoding="utf-8"))

    assert saved_data == {"2024-03-03_USD_CAD": 1.4}



def test_fetch_with_base_currency_and_not_unity_returns_rate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """HTTP 200 payload with expected rate should return that rate."""

    getter = _build_getter(tmp_path)

    def fake_get(url: str) -> _FakeResponse:
        assert "historical/2024-02-01.json" in url
        assert "symbols=EUR" in url
        return _FakeResponse(status_code=200, payload={"rates": {"EUR": 0.92}})

    monkeypatch.setattr(exchange_rates.requests, "get", fake_get)

    result = getter._fetch_from_api_with_base_currency_and_not_unity("2024-02-01", "EUR")

    assert result == 0.92



def test_fetch_with_base_currency_and_not_unity_raises_for_non_200(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Non-success response should raise a detailed wrapped exception."""

    getter = _build_getter(tmp_path)

    def fake_get(_url: str) -> _FakeResponse:
        return _FakeResponse(status_code=500, payload={}, text="boom")

    monkeypatch.setattr(exchange_rates.requests, "get", fake_get)

    with pytest.raises(Exception, match="Error fetching exchange rate 'USD -> EUR' on 2024-02-01"):
        getter._fetch_from_api_with_base_currency_and_not_unity("2024-02-01", "EUR")



def test_fetch_with_base_currency_and_not_unity_raises_for_bad_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Invalid JSON response should raise with JSON decoding context."""

    getter = _build_getter(tmp_path)

    decode_error = json.JSONDecodeError("bad json", "{", 0)

    def fake_get(_url: str) -> _FakeResponse:
        return _FakeResponse(status_code=200, payload=decode_error)

    monkeypatch.setattr(exchange_rates.requests, "get", fake_get)

    with pytest.raises(Exception, match="Error decoding JSON response"):
        getter._fetch_from_api_with_base_currency_and_not_unity("2024-02-01", "EUR")



def test_fetch_with_base_currency_and_not_unity_raises_for_missing_currency_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Missing target currency entry should raise explicit failure."""

    getter = _build_getter(tmp_path)

    def fake_get(_url: str) -> _FakeResponse:
        return _FakeResponse(status_code=200, payload={"rates": {"JPY": 150.0}})

    monkeypatch.setattr(exchange_rates.requests, "get", fake_get)

    with pytest.raises(Exception, match="Exchange rate data not available for EUR"):
        getter._fetch_from_api_with_base_currency_and_not_unity("2024-02-01", "EUR")



def test_fetch_with_base_currency_returns_unity_for_usd(tmp_path: Path) -> None:
    """USD target should short-circuit to 1.0 without API calls."""

    getter = _build_getter(tmp_path)

    result = getter._fetch_from_api_with_base_currency("2024-01-01", "USD")

    assert result == 1.0



def test_fetch_from_api_uses_ratio_formula(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cross-currency conversion should divide target and base USD rates."""

    getter = _build_getter(tmp_path)

    def fake_fetch(_date_str: str, currency: str) -> float:
        rates = {"EUR": 0.8, "GBP": 0.5}
        return rates[currency]

    monkeypatch.setattr(getter, "_fetch_from_api_with_base_currency", fake_fetch)

    result = getter._fetch_from_api("2024-01-01", "GBP", "EUR")

    assert result == pytest.approx(1.6)



def test_get_exchange_rate_raises_for_invalid_date_type(tmp_path: Path) -> None:
    """Invalid date value should raise ValueError."""

    getter = _build_getter(tmp_path)

    with pytest.raises(ValueError, match="must be a datetime.date"):
        getter.get_exchange_rate("2024-01-01", "USD", "EUR")



def test_get_exchange_rate_returns_cached_value_without_fetch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cache hit should not call API fetch helper."""

    getter = _build_getter(tmp_path)
    getter.cache["2024-01-01_USD_EUR"] = 0.91

    def fail_fetch(*_args: object, **_kwargs: object) -> float:
        raise AssertionError("fetch should not be called on cache hit")

    monkeypatch.setattr(getter, "_fetch_from_api", fail_fetch)

    result = getter.get_exchange_rate(datetime.date(2024, 1, 1), "USD", "EUR")

    assert result == 0.91



def test_get_exchange_rate_fetches_and_saves_on_cache_miss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cache miss should fetch result, store it, and persist cache."""

    getter = _build_getter(tmp_path)

    def fake_fetch(_date_str: str, _base: str, _target: str) -> float:
        return 1.23

    monkeypatch.setattr(getter, "_fetch_from_api", fake_fetch)

    result = getter.get_exchange_rate(datetime.date(2024, 6, 10), "USD", "CAD")

    assert result == 1.23
    assert getter.cache["2024-06-10_USD_CAD"] == 1.23

    saved_data = json.loads(Path(getter.path_to_cache).read_text(encoding="utf-8"))
    assert saved_data["2024-06-10_USD_CAD"] == 1.23



def test_get_exchange_rate_does_not_save_when_fetch_returns_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """None rate should be returned directly and not persisted."""

    getter = _build_getter(tmp_path)

    def fake_fetch(_date_str: str, _base: str, _target: str) -> None:
        return None

    monkeypatch.setattr(getter, "_fetch_from_api", fake_fetch)

    result = getter.get_exchange_rate(datetime.date(2024, 6, 10), "USD", "CAD")

    assert result is None
    assert getter.cache == {}
    assert not Path(getter.path_to_cache).exists()
