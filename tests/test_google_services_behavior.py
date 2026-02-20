"""Unit tests for GoogleServices behavior without real API calls."""

from __future__ import annotations

import socket
from unittest.mock import Mock

import pytest

import sys
import types


def _install_google_stubs() -> None:
    """Install lightweight google modules so tests can import google_services."""

    google_module = types.ModuleType("google")
    auth_module = types.ModuleType("google.auth")
    transport_module = types.ModuleType("google.auth.transport")
    requests_module = types.ModuleType("google.auth.transport.requests")
    oauth2_module = types.ModuleType("google.oauth2")
    credentials_module = types.ModuleType("google.oauth2.credentials")
    oauthlib_module = types.ModuleType("google_auth_oauthlib")
    flow_module = types.ModuleType("google_auth_oauthlib.flow")
    apiclient_module = types.ModuleType("googleapiclient")
    discovery_module = types.ModuleType("googleapiclient.discovery")
    errors_module = types.ModuleType("googleapiclient.errors")
    http_module = types.ModuleType("googleapiclient.http")

    class _Request:  # noqa: D401
        pass

    class _Credentials:
        valid = True
        expired = False
        refresh_token = None

        @classmethod
        def from_authorized_user_file(cls, *_args, **_kwargs):
            return cls()

        @classmethod
        def from_authorized_user_info(cls, *_args, **_kwargs):
            return cls()

        def refresh(self, *_args, **_kwargs):
            return None

        def to_json(self):
            return "{}"

    class _Flow:
        @classmethod
        def from_client_secrets_file(cls, *_args, **_kwargs):
            return cls()

        @classmethod
        def from_client_config(cls, *_args, **_kwargs):
            return cls()

        def run_local_server(self, *_args, **_kwargs):
            return _Credentials()

    class _HttpError(Exception):
        def __init__(self, resp=None, content=b""):
            super().__init__(str(content))
            self.resp = resp
            self.content = content

    class _MediaFileUpload:
        def __init__(self, *_args, **_kwargs):
            pass

    requests_module.Request = _Request
    credentials_module.Credentials = _Credentials
    flow_module.InstalledAppFlow = _Flow
    discovery_module.build = lambda *_args, **_kwargs: None
    errors_module.HttpError = _HttpError
    http_module.MediaFileUpload = _MediaFileUpload

    sys.modules.setdefault("google", google_module)
    sys.modules.setdefault("google.auth", auth_module)
    sys.modules.setdefault("google.auth.transport", transport_module)
    sys.modules.setdefault("google.auth.transport.requests", requests_module)
    sys.modules.setdefault("google.oauth2", oauth2_module)
    sys.modules.setdefault("google.oauth2.credentials", credentials_module)
    sys.modules.setdefault("google_auth_oauthlib", oauthlib_module)
    sys.modules.setdefault("google_auth_oauthlib.flow", flow_module)
    sys.modules.setdefault("googleapiclient", apiclient_module)
    sys.modules.setdefault("googleapiclient.discovery", discovery_module)
    sys.modules.setdefault("googleapiclient.errors", errors_module)
    sys.modules.setdefault("googleapiclient.http", http_module)


_install_google_stubs()

from julien_python_toolkit import google_services  # noqa: E402



def _build_service(monkeypatch: pytest.MonkeyPatch) -> google_services.GoogleServices:
    """Create a GoogleServices instance without opening remote sessions."""

    monkeypatch.setattr(google_services.GoogleServices, "open", lambda self: None)
    return google_services.GoogleServices(
        credentials_info={"installed": {"client_id": "test"}},
        token_info={"token": "test"},
    )


def test_init_accepts_new_in_memory_oauth_info(monkeypatch: pytest.MonkeyPatch) -> None:
    """Constructor should keep dict-based oauth info in memory mode."""

    monkeypatch.setattr(google_services.GoogleServices, "open", lambda self: None)
    service = google_services.GoogleServices(
        credentials_info={"installed": {"client_id": "abc"}},
        token_info={"token": "xyz"},
    )

    assert service._use_legacy_file_auth is False
    assert service._credentials_info == {"installed": {"client_id": "abc"}}
    assert service._token_info == {"token": "xyz"}


def test_init_maps_old_positional_paths_and_warns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Old positional path style should still work with a deprecation warning."""

    monkeypatch.setattr(google_services.GoogleServices, "open", lambda self: None)

    with pytest.warns(FutureWarning, match="deprecated"):
        service = google_services.GoogleServices("credentials.json", "token.json")

    assert service._use_legacy_file_auth is True
    assert service._path_to_credentials_file == "credentials.json"
    assert service._path_to_token_file == "token.json"


def test_open_uses_token_info_when_in_memory_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """open should read token data from token_info in in-memory mode."""

    credential_mock = Mock(valid=True)
    from_authorized_user_info_mock = Mock(return_value=credential_mock)
    build_mock = Mock(return_value=Mock())

    monkeypatch.setattr(google_services.Credentials, "from_authorized_user_info", from_authorized_user_info_mock)
    monkeypatch.setattr(google_services, "build", build_mock)

    google_services.GoogleServices(
        credentials_info={"installed": {"client_id": "abc"}},
        token_info={"token": "xyz"},
    )

    from_authorized_user_info_mock.assert_called_once_with({"token": "xyz"}, google_services.GoogleServices._SCOPES)
    assert build_mock.call_count == 2



def test_retry_if_network_error_retries_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Decorator should retry temporary network errors then return success."""

    sleep_mock = Mock()
    monkeypatch.setattr(google_services.time, "sleep", sleep_mock)

    state = {"calls": 0}

    @google_services.GoogleServices.retry_if_network_error
    def flaky_call() -> str:
        state["calls"] += 1
        if state["calls"] < 3:
            raise TimeoutError("temporary")
        return "ok"

    assert flaky_call() == "ok"
    assert state["calls"] == 3
    assert sleep_mock.call_args_list[0].args == (2,)
    assert sleep_mock.call_args_list[1].args == (4,)



def test_retry_if_network_error_raises_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Decorator should stop after max retries and raise TimeoutError."""

    monkeypatch.setattr(google_services.time, "sleep", lambda _: None)

    @google_services.GoogleServices.retry_if_network_error
    def always_fails() -> None:
        raise socket.timeout("network")

    with pytest.raises(TimeoutError, match="Exceeded maximum retries"):
        always_fails()



def test_retry_if_network_error_does_not_retry_non_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Decorator should immediately re-raise non-network errors."""

    sleep_mock = Mock()
    monkeypatch.setattr(google_services.time, "sleep", sleep_mock)

    @google_services.GoogleServices.retry_if_network_error
    def fail_fast() -> None:
        raise ValueError("bad input")

    with pytest.raises(ValueError, match="bad input"):
        fail_fast()

    sleep_mock.assert_not_called()



def test_duplicate_sheet_calls_batch_update_with_expected_body(monkeypatch: pytest.MonkeyPatch) -> None:
    """duplicate_sheet should build request body and delegate to batch update."""

    service = _build_service(monkeypatch)
    service.batch_update_spreadsheet = Mock(return_value={"done": True})

    response = service.duplicate_sheet("spreadsheet-1", 123, 0, "Copy Sheet")

    assert response == {"done": True}
    service.batch_update_spreadsheet.assert_called_once_with(
        "spreadsheet-1",
        {
            "requests": [
                {
                    "duplicateSheet": {
                        "sourceSheetId": 123,
                        "insertSheetIndex": 0,
                        "newSheetName": "Copy Sheet",
                    }
                }
            ]
        },
    )



def test_duplicate_sheet_rejects_long_sheet_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """duplicate_sheet should fail when the new sheet name exceeds 50 chars."""

    service = _build_service(monkeypatch)

    with pytest.raises(Exception, match="max. is 50"):
        service.duplicate_sheet("spreadsheet-1", 123, 0, "x" * 51)



def test_delete_sheets_from_spreadsheet_rejects_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """delete_sheets_from_spreadsheet should reject empty id lists."""

    service = _build_service(monkeypatch)

    with pytest.raises(Exception, match="is empty"):
        service.delete_sheets_from_spreadsheet("spreadsheet-1", [])



def test_delete_sheets_from_spreadsheet_builds_delete_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    """delete_sheets_from_spreadsheet should send one delete request per sheet."""

    service = _build_service(monkeypatch)
    service.batch_update_spreadsheet = Mock(return_value={"done": True})

    response = service.delete_sheets_from_spreadsheet("spreadsheet-1", [11, 22])

    assert response == {"done": True}
    service.batch_update_spreadsheet.assert_called_once_with(
        "spreadsheet-1",
        {"requests": [{"deleteSheet": {"sheetId": 11}}, {"deleteSheet": {"sheetId": 22}}]},
    )



def test_reorder_all_sheets_in_spreadsheet_rejects_duplicate_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """reorder_all_sheets_in_spreadsheet should reject duplicate ids in new order."""

    service = _build_service(monkeypatch)

    with pytest.raises(Exception, match="contains duplicate"):
        service.reorder_all_sheets_in_spreadsheet("spreadsheet-1", [1, 1])



def test_reorder_all_sheets_in_spreadsheet_rejects_non_matching_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """reorder_all_sheets_in_spreadsheet should fail on set mismatch."""

    service = _build_service(monkeypatch)
    service.get_sheets_medatada_from_sheet = Mock(return_value=[{"properties": {"sheetId": 1}}])

    with pytest.raises(Exception, match="are not the same"):
        service.reorder_all_sheets_in_spreadsheet("spreadsheet-1", [2])



def test_reorder_all_sheets_in_spreadsheet_builds_reorder_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    """reorder_all_sheets_in_spreadsheet should send index updates for all sheets."""

    service = _build_service(monkeypatch)
    service.get_sheets_medatada_from_sheet = Mock(
        return_value=[
            {"properties": {"sheetId": 100}},
            {"properties": {"sheetId": 200}},
        ]
    )
    service.batch_update_spreadsheet = Mock(return_value={"ok": True})

    response = service.reorder_all_sheets_in_spreadsheet("spreadsheet-1", [200, 100])

    assert response == {"ok": True}
    service.batch_update_spreadsheet.assert_called_once_with(
        "spreadsheet-1",
        {
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": 200, "index": 0},
                        "fields": "index",
                    }
                },
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": 100, "index": 1},
                        "fields": "index",
                    }
                },
            ]
        },
    )
