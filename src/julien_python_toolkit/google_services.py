# This file is part of the "your-package-name" project.
# It is licensed under the "Custom Non-Commercial License".
# You may not use this file for commercial purposes without
# explicit permission from the author.


import json
import os
import socket
import ssl
import time
import warnings
from collections.abc import Callable
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-untyped]
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]
from googleapiclient.http import MediaFileUpload  # type: ignore[import-untyped]

from . import log_utilities


# Global Variables
PATH_TO_THIS_FILE = os.path.dirname(os.path.realpath(__file__))


# Set Up Logger
logger = log_utilities.Logger(
    "GoogleServices",
    "google_services.log",
    stream_log_level=log_utilities.WARNING,
    file_log_level=log_utilities.WARNING,
)


class GoogleServices:
    """Helper class for Google Sheets and Google Drive operations."""

    # How to use:
    # 1. Download credentials.json file from Google Cloud Console (see tutorial below).

    # NOTE: For drive access, you can only do it for personal drive, not shared drives.

    # Tutorial: https://www.youtube.com/watch?v=3wC-SCdJK2c&t=315s

    _SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    # Need to perform the OAuth2 authorization flow once for the new spreadsheet,
    # and it will generate a new token file specific to that spreadsheet.
    _DEFAULT_PATH_TO_CREDENTIALS_FILE = os.path.join(PATH_TO_THIS_FILE, "credentials.json")
    _DEFAULT_PATH_TO_TOKEN_FILE = os.path.join(PATH_TO_THIS_FILE, "token.json")
    _LEGACY_FILE_MODE_REMOVAL_DATE = "2026-08-01"

    @staticmethod
    def retry_if_network_error(func: Callable[..., Any]) -> Callable[..., Any]:
        """Retry wrapped calls when temporary network or server errors occur.

        Args:
            func: Callable to wrap with retry behavior.

        Returns:
            Wrapped callable that retries on transient network failures.
        """

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0

            while retries < 10:
                try:
                    return func(*args, **kwargs)

                except Exception as error:
                    # NOTE: Add all the errors to retry here.
                    is_timeout_error = isinstance(error, TimeoutError)
                    is_too_many_requests_error = isinstance(error, HttpError) and error.__cause__.resp.status == 429
                    is_internal_server_error = isinstance(error, HttpError) and error.__cause__.resp.status == 500
                    is_bad_gateway_error = isinstance(error, HttpError) and error.__cause__.resp.status == 502
                    is_server_unavailable_error = isinstance(error, HttpError) and error.__cause__.resp.status == 503
                    is_socket_timeout_error = isinstance(error, socket.timeout)
                    is_socket_gaierror = isinstance(error, socket.gaierror)
                    is_ssl_error = isinstance(error, ssl.SSLError)

                    if (
                        is_timeout_error
                        or is_too_many_requests_error
                        or is_internal_server_error
                        or is_bad_gateway_error
                        or is_server_unavailable_error
                        or is_socket_timeout_error
                        or is_socket_gaierror
                        or is_ssl_error
                    ):
                        logger.warn(
                            f"Function '{func.__name__}' network error. Retrying. "
                            f"Retry count: {retries + 1}/8. Curent delay: {2 ** (retries + 1)} seconds. "
                            f"Error = {error.__class__}({error})."
                        )

                        retries += 1
                        delay = 2**retries
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Function '{func.__name__}' raised an error. "
                            f"Error = {error.__class__}({error})."
                        )

                        raise error from error

            raise TimeoutError("Exceeded maximum retries.")

        return wrapper

    def __init__(
        self,
        credentials_info: dict[str, Any] | str | None = None,
        token_info: dict[str, Any] | str | None = None,
        path_to_credentials_file: str | None = None,
        path_to_token_file: str | None = None,
    ) -> None:
        """Create Google service clients and open authenticated sessions.

        Args:
            credentials_info: OAuth client credentials as a dict (or JSON string).
            token_info: OAuth token values as a dict (or JSON string).
            path_to_credentials_file: Optional path to a Google OAuth credentials file.
            path_to_token_file: Optional path to the cached OAuth token file.
        """

        # Backward compatibility:
        # if first and second args are path-like strings, treat them as old file paths.
        if self._looks_like_legacy_path_args(credentials_info, token_info, path_to_credentials_file, path_to_token_file):
            path_to_credentials_file = str(credentials_info)
            path_to_token_file = str(token_info)
            credentials_info = None
            token_info = None
        elif (
            isinstance(credentials_info, str)
            and not self._is_json_object_string(credentials_info)
            and path_to_credentials_file is None
        ):
            # Backward compatibility for old one-arg style:
            # GoogleServices("credentials.json")
            path_to_credentials_file = credentials_info
            credentials_info = None

        self._credentials_info = self._normalize_oauth_info(credentials_info, "credentials_info")
        self._token_info = self._normalize_oauth_info(token_info, "token_info")

        # Prefer new in-memory mode when credentials/token info is provided.
        self._use_legacy_file_auth = self._credentials_info is None and self._token_info is None

        if self._use_legacy_file_auth:
            if path_to_credentials_file is None:
                path_to_credentials_file = self._DEFAULT_PATH_TO_CREDENTIALS_FILE

            if path_to_token_file is None:
                path_to_token_file = self._DEFAULT_PATH_TO_TOKEN_FILE

            self._warn_legacy_file_mode()
        elif path_to_credentials_file is not None or path_to_token_file is not None:
            warnings.warn(
                "You passed both in-memory auth info and file paths. "
                "File paths are ignored because in-memory auth is used.",
                UserWarning,
                stacklevel=2,
            )

        self._path_to_credentials_file = path_to_credentials_file
        self._path_to_token_file = path_to_token_file
        self._sheet_service = None
        self._drive_service = None

        self.open()

    @staticmethod
    def _is_json_object_string(value: str) -> bool:
        """Return True when a string looks like a JSON object."""

        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            return False

        return isinstance(parsed_value, dict)

    @classmethod
    def _looks_like_legacy_path_args(
        cls,
        credentials_info: dict[str, Any] | str | None,
        token_info: dict[str, Any] | str | None,
        path_to_credentials_file: str | None,
        path_to_token_file: str | None,
    ) -> bool:
        """Detect old positional style: GoogleServices('credentials.json', 'token.json')."""

        return (
            isinstance(credentials_info, str)
            and isinstance(token_info, str)
            and not cls._is_json_object_string(credentials_info)
            and not cls._is_json_object_string(token_info)
            and path_to_credentials_file is None
            and path_to_token_file is None
        )

    @staticmethod
    def _normalize_oauth_info(
        oauth_info: dict[str, Any] | str | None,
        variable_name: str,
    ) -> dict[str, Any] | None:
        """Accept dict or JSON string for OAuth info and return a dict."""

        if oauth_info is None:
            return None

        if isinstance(oauth_info, dict):
            return oauth_info

        if isinstance(oauth_info, str):
            try:
                parsed_oauth_info = json.loads(oauth_info)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{variable_name} must be a dict or valid JSON string."
                ) from error

            if isinstance(parsed_oauth_info, dict):
                return parsed_oauth_info

        raise ValueError(f"{variable_name} must be a dict or valid JSON string.")
    
    @property
    def token_info(self) -> dict[str, Any] | None:
        """Return the current token info as a dict, or None if not available."""

        return self._token_info

    def _warn_legacy_file_mode(self) -> None:
        """Warn users that file path auth mode is scheduled for removal."""

        deprecation_message = (
            "GoogleServices file-path auth mode is deprecated and will be removed after "
            f"{self._LEGACY_FILE_MODE_REMOVAL_DATE}. "
            "Please pass credentials_info and token_info to the constructor."
        )
        warnings.warn(deprecation_message, FutureWarning, stacklevel=3)
        logger.warn(deprecation_message)

    def open(self) -> None:
        """Authenticate and initialize Google Sheets and Drive clients.

        Raises:
            Exception: If authentication or client initialization fails.
        """

        try:
            credentials = None

            if self._use_legacy_file_auth:
                # TODO(deprecation): Remove file-based auth loading after 2026-08-01.
                # A. If there is a token file, get credentials from token file.
                if self._path_to_token_file is None:
                    raise Exception("path_to_token_file is required in legacy auth mode.")
                if os.path.exists(self._path_to_token_file):
                    credentials = Credentials.from_authorized_user_file(self._path_to_token_file, self._SCOPES)
            elif self._token_info is not None:
                # New mode: read token directly from in-memory data.
                credentials = Credentials.from_authorized_user_info(self._token_info, self._SCOPES)

            # B. If credentials are not valid or do not exist.
            if not credentials or not credentials.valid:
                # a. If credentials exist but are expired -> refresh token.
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                # b. Else -> get credentials from server (i.e. login).
                else:
                    if self._use_legacy_file_auth:
                        # TODO(deprecation): Remove file-based auth loading after 2026-08-01.
                        if self._path_to_credentials_file is None:
                            raise Exception("path_to_credentials_file is required in legacy auth mode.")
                        flow = InstalledAppFlow.from_client_secrets_file(self._path_to_credentials_file, self._SCOPES)
                    else:
                        if self._credentials_info is None:
                            raise Exception(
                                "credentials_info is required when token_info is missing or not valid."
                            )
                        flow = InstalledAppFlow.from_client_config(self._credentials_info, self._SCOPES)

                    credentials = flow.run_local_server(port=0)

                if self._use_legacy_file_auth:
                    # TODO(deprecation): Remove file-based token write after 2026-08-01.
                    # Update the token file.
                    if self._path_to_token_file is None:
                        raise Exception("path_to_token_file is required in legacy auth mode.")
                    with open(self._path_to_token_file, "w") as token:
                        token.write(credentials.to_json())
                else:
                    # Keep refreshed token in memory so caller can save it.
                    self._token_info = json.loads(credentials.to_json())

            self._sheet_service = build("sheets", "v4", credentials=credentials)
            self._drive_service = build("drive", "v3", credentials=credentials)

        except Exception as error:
            raise Exception(f"Error initializing Google services: {error}")

    @retry_if_network_error
    def batch_update_spreadsheet(self, spreadsheet_id: str, body: dict[str, Any]) -> dict[str, Any]:
        """Run a ``batchUpdate`` request on a Google spreadsheet.

        Args:
            spreadsheet_id: Target spreadsheet id.
            body: Request payload accepted by Google Sheets ``batchUpdate``.

        Returns:
            API response payload returned by Google Sheets.
        """

        if self._sheet_service is None:
            raise Exception("Spreadsheet service is not initialized. Please run the 'open' function.")

        try:
            response = self._sheet_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body,
            ).execute()

            return response

        except HttpError as error:
            error_content = f"HttpError from {self.batch_update_spreadsheet.__name__}: {error.content}".encode("utf-8")
            raise HttpError(resp=error.resp, content=error_content) from error

    @retry_if_network_error
    def write_csv_to_sheet(self, csv_data: list[list[Any]], spreadsheet_id: str, sheet_name: str) -> None:
        """Write a 2D value list to a sheet starting at cell ``A1``.

        Args:
            csv_data: Table-like list of rows and values.
            spreadsheet_id: Target spreadsheet id.
            sheet_name: Name of the sheet tab to update.
        """

        if self._sheet_service is None:
            raise Exception("Spreadsheet service is not initialized. Please run the 'open' function.")

        try:
            self._sheet_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption="USER_ENTERED",
                body={"values": csv_data},
            ).execute()

        except HttpError as error:
            error_content = f"HttpError from {self.write_csv_to_sheet.__name__}: {error.content}".encode("utf-8")
            raise HttpError(resp=error.resp, content=error_content) from error

    @retry_if_network_error
    def write_csv_to_range(
        self,
        csv_data: list[list[Any]],
        spreadsheet_id: str,
        sheet_name: str,
        range_name: str,
    ) -> None:
        """Write a 2D value list to a specific sheet range.

        Args:
            csv_data: Table-like list of rows and values.
            spreadsheet_id: Target spreadsheet id.
            sheet_name: Name of the sheet tab to update.
            range_name: A1-style range inside ``sheet_name``.
        """

        if self._sheet_service is None:
            raise Exception("Spreadsheet service is not initialized. Please run the 'open' function.")

        try:
            self._sheet_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!{range_name}",
                valueInputOption="USER_ENTERED",
                body={"values": csv_data},
            ).execute()

        except HttpError as error:
            error_content = f"HttpError from {self.write_csv_to_range.__name__}: {error.content}".encode("utf-8")
            raise HttpError(resp=error.resp, content=error_content) from error

    @retry_if_network_error
    def write_data_to_sheet_batch_update(
        self,
        ranges: list[str],
        values: list[list[list[Any]]],
        spreadsheet_id: str,
    ) -> dict[str, Any]:
        """Batch update many ranges in one spreadsheet API call.

        Args:
            ranges: List of A1-style ranges to update.
            values: Data payload for each corresponding range.
            spreadsheet_id: Target spreadsheet id.

        Returns:
            API response payload returned by Google Sheets.
        """

        # TODO: Modify to use 'batch_update_spreadsheet' function to avoid code duplication.

        if self._sheet_service is None:
            raise Exception("Spreadsheet service is not initialized. Please run the 'open' function.")

        # Create values list of dict.
        value_list = []
        for range_name, data in zip(ranges, values):
            value_dict = {"range": range_name, "values": data}
            value_list.append(value_dict)

        try:
            body = {
                "valueInputOption": "USER_ENTERED",
                "data": value_list,
            }

            response = self._sheet_service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body,
            ).execute()

            return response

        except HttpError as error:
            error_content = f"HttpError from {self.write_data_to_sheet_batch_update.__name__}: {error.content}".encode("utf-8")
            raise HttpError(resp=error.resp, content=error_content) from error

    @retry_if_network_error
    def read_csv_from_sheet(self, spreadsheet_id: str, sheet_name: str) -> list[list[Any]]:
        """Read values from an entire sheet and return a 2D list.

        Args:
            spreadsheet_id: Target spreadsheet id.
            sheet_name: Name of the sheet tab to read.

        Returns:
            A list of rows read from the requested sheet.
        """

        if self._sheet_service is None:
            raise Exception("Spreadsheet service is not initialized. Please run the 'open' function.")

        try:
            result = self._sheet_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=sheet_name,
            ).execute()

            return result.get("values", [])

        except HttpError as error:
            error_content = f"HttpError from {self.read_csv_from_sheet.__name__}: {error.content}".encode("utf-8")
            raise HttpError(resp=error.resp, content=error_content) from error

    @retry_if_network_error
    def read_csv_from_range(self, spreadsheet_id: str, sheet_name: str, range_name: str) -> list[list[Any]]:
        """Read values from one sheet range and return a 2D list.

        Args:
            spreadsheet_id: Target spreadsheet id.
            sheet_name: Name of the sheet tab to read.
            range_name: A1-style range inside ``sheet_name``.

        Returns:
            A list of rows read from the requested range.
        """

        if self._sheet_service is None:
            raise Exception("Spreadsheet service is not initialized. Please run the 'open' function.")

        try:
            result = self._sheet_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!{range_name}",
            ).execute()

            return result.get("values", [])

        except HttpError as error:
            error_content = f"HttpError from {self.read_csv_from_range.__name__}: {error.content}".encode("utf-8")
            raise HttpError(resp=error.resp, content=error_content) from error

    @retry_if_network_error
    def get_sheet_names_from_sheet(self, spreadsheet_id: str) -> list[str]:
        """Return all worksheet names in a spreadsheet.

        Args:
            spreadsheet_id: Target spreadsheet id.

        Returns:
            List containing each worksheet title.
        """

        logger.warning(f"Method '{self.get_sheet_names_from_sheet.__name__}' will be depreciated in a future version.")

        # TODO: Use 'get_sheets_medatada_from_sheet' to get sheets metadata and then get sheets names,
        # to avoid code duplication.
        if self._sheet_service is None:
            raise Exception("Spreadsheet service is not initialized. Please run the 'open' function.")

        try:
            spreadsheet = self._sheet_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

            sheets = spreadsheet.get("sheets", [])
            sheet_names = [sheet["properties"]["title"] for sheet in sheets]

            return sheet_names

        except HttpError as error:
            error_content = f"HttpError from {self.get_sheet_names_from_sheet.__name__}: {error.content}".encode("utf-8")
            raise HttpError(resp=error.resp, content=error_content) from error

    @retry_if_network_error
    def get_sheets_medatada_from_sheet(self, spreadsheet_id: str) -> list[dict[str, Any]]:
        """Return raw metadata entries for all sheets in a spreadsheet.

        Args:
            spreadsheet_id: Target spreadsheet id.

        Returns:
            Raw sheet metadata objects returned by Google Sheets.
        """

        if self._sheet_service is None:
            raise Exception("Spreadsheet service is not initialized. Please run the 'open' function.")

        try:
            spreadsheet = self._sheet_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

            sheets_metadata = spreadsheet.get("sheets", [])
            return sheets_metadata

        except HttpError as error:
            error_content = f"HttpError from {self.get_sheets_medatada_from_sheet.__name__}: {error.content}".encode("utf-8")
            raise HttpError(resp=error.resp, content=error_content) from error

    def get_subfolders_in_folder(self, folder_id: str) -> list[dict[str, Any]]:
        """List subfolders inside a Drive folder.

        Args:
            folder_id: Parent Drive folder id.

        Returns:
            List of folder metadata dictionaries.
        """

        if self._drive_service is None:
            raise Exception("Drive service is not initialized. Please run the 'open' function.")

        try:
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = self._drive_service.files().list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name)",
            ).execute()
            folders = response.get("files", [])

            return folders

        except Exception as error:
            raise Exception(f"Error getting subfolders: {error}")

    def get_all_files_in_folder(self, folder_id: str) -> list[dict[str, Any]]:
        """List all files inside a Drive folder.

        Args:
            folder_id: Parent Drive folder id.

        Returns:
            List of file metadata dictionaries.
        """

        if self._drive_service is None:
            raise Exception("Drive service is not initialized. Please run the 'open' function.")

        try:
            query = f"'{folder_id}' in parents and trashed=false"
            response = self._drive_service.files().list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
            ).execute()
            files = response.get("files", [])

            return files

        except Exception as error:
            raise Exception(f"Error getting files in folder: {error}")

    def create_folder(self, new_folder_name: str, parent_folder_id: str) -> str:
        """Create a folder in Drive and return its new folder id.

        Args:
            new_folder_name: Name to assign to the new folder.
            parent_folder_id: Drive folder id where the new folder is created.

        Returns:
            The id of the newly created folder.
        """

        if self._drive_service is None:
            raise Exception("Drive service is not initialized. Please run the 'open' function.")

        try:
            file_metadata = {
                "name": new_folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_folder_id],
            }

            folder = self._drive_service.files().create(body=file_metadata, fields="id").execute()
            return folder.get("id")

        except Exception as error:
            raise Exception(f"Error creating folder: {error}")

    def check_if_subfolder_exists_in_folder(self, folder_id: str, subfolder_name: str) -> tuple[bool, str | None]:
        """Check if a named subfolder exists and return status plus id.

        Args:
            folder_id: Parent Drive folder id.
            subfolder_name: Subfolder name to look up.

        Returns:
            Tuple of ``(exists, subfolder_id)`` where ``subfolder_id`` is ``None`` when absent.
        """

        if self._drive_service is None:
            raise Exception("Drive service is not initialized. Please run the 'open' function.")

        try:
            query = f"'{folder_id}' in parents and name='{subfolder_name}' and trashed=false"
            response = self._drive_service.files().list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name)",
            ).execute()
            items = response.get("files", [])

            if items:
                return True, items[0]["id"]
            else:
                return False, None

        except Exception as error:
            raise Exception(f"Error checking if subfolder exists: {error}")

    def check_if_folder_exists(self, folder_id: str) -> bool:
        """Return ``True`` when Drive folder exists and is not trashed.

        Args:
            folder_id: Drive folder id to validate.

        Returns:
            ``True`` when the folder exists and is active, otherwise ``False``.
        """

        if self._drive_service is None:
            raise Exception("Drive service is not initialized. Please run the 'open' function.")

        try:
            response = self._drive_service.files().get(fileId=folder_id, fields="id, trashed").execute()

            if "trashed" in response and response["trashed"]:
                return False

            return True

        except HttpError as error:
            if error.resp.status == 404:
                return False
            else:
                raise Exception(f"Error checking if folder exists: {error}")

    def upload_file_to_folder(self, file_path: str, folder_id: str, mime_type: str | None = None) -> None:
        """Upload one local file to a Drive folder.

        Args:
            file_path: Local path of the file to upload.
            folder_id: Destination Drive folder id.
            mime_type: MIME type for the uploaded file.
        """

        # Mime type for PNG image = 'image/png'
        if mime_type is None:
            raise Exception("Mime type is not provided.")

        if self._drive_service is None:
            raise Exception("Drive service is not initialized. Please run the 'open' function.")

        try:
            file_metadata = {
                "name": os.path.basename(file_path),
                "parents": [folder_id],
            }

            media = MediaFileUpload(file_path, mimetype=mime_type)
            self._drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        except Exception as error:
            raise Exception(f"Error uploading file to folder: {error}")

    # Non network functions.

    def duplicate_sheet(
        self,
        spreadsheet_id: str,
        source_sheet_id: int,
        insert_index: int,
        new_sheet_name: str,
    ) -> dict[str, Any]:
        """Duplicate a sheet and insert it at the provided index.

        Args:
            spreadsheet_id: Target spreadsheet id.
            source_sheet_id: Sheet id to duplicate.
            insert_index: Target index for the duplicated sheet.
            new_sheet_name: New title for the duplicated sheet.

        Returns:
            API response payload returned by Google Sheets.
        """

        if not isinstance(source_sheet_id, int):
            raise Exception(f"Source sheet id '{source_sheet_id}' is not an integer.")

        if not isinstance(insert_index, int):
            raise Exception(f"Insert index '{insert_index}' is not an integer.")

        if not isinstance(new_sheet_name, str):
            raise Exception(f"New sheet name '{new_sheet_name}' is not a string.")

        if len(new_sheet_name) > 50:
            raise Exception(
                f"New sheet name '{new_sheet_name}' has {len(new_sheet_name)} characters, "
                "but max. is 50 characters."
            )

        request_body = {
            "requests": [
                {
                    "duplicateSheet": {
                        "sourceSheetId": source_sheet_id,
                        "insertSheetIndex": insert_index,
                        "newSheetName": new_sheet_name,
                    }
                }
            ]
        }

        return self.batch_update_spreadsheet(spreadsheet_id, request_body)

    def delete_sheets_from_spreadsheet(self, spreadsheet_id: str, ids_of_sheets_to_delete: list[int]) -> dict[str, Any]:
        """Delete one or many sheets from a spreadsheet by id.

        Args:
            spreadsheet_id: Target spreadsheet id.
            ids_of_sheets_to_delete: Sheet ids that should be removed.

        Returns:
            API response payload returned by Google Sheets.
        """

        if not isinstance(ids_of_sheets_to_delete, list):
            raise Exception(f"Sheet ids '{ids_of_sheets_to_delete}' is not a list.")

        if len(ids_of_sheets_to_delete) == 0:
            raise Exception(f"Sheet ids list '{ids_of_sheets_to_delete}' is empty.")

        requests = []
        for sheet_id in ids_of_sheets_to_delete:
            requests.append({"deleteSheet": {"sheetId": sheet_id}})

        request_body = {"requests": requests}

        return self.batch_update_spreadsheet(spreadsheet_id, request_body)

    def reorder_all_sheets_in_spreadsheet(self, spreadsheet_id: str, sheet_ids_in_new_order: list[int]) -> dict[str, Any]:
        """Reorder all sheets using a full list of sheet ids in new order.

        Args:
            spreadsheet_id: Target spreadsheet id.
            sheet_ids_in_new_order: Complete sheet id order to apply.

        Returns:
            API response payload returned by Google Sheets.
        """

        # Step 0: Initial checks.
        if not isinstance(sheet_ids_in_new_order, list):
            raise Exception(f"Sheet names '{sheet_ids_in_new_order}' is not a list.")

        if len(sheet_ids_in_new_order) == 0:
            raise Exception(f"Sheet names list '{sheet_ids_in_new_order}' is empty.")

        # Step 1: Check that each sheet id is an integer.
        for sheet_id in sheet_ids_in_new_order:
            if not isinstance(sheet_id, int):
                raise Exception(f"Sheet id '{sheet_id}' is not an integer.")

        # Step 2: Check that there are no duplicate sheet ids.
        if len(sheet_ids_in_new_order) != len(set(sheet_ids_in_new_order)):
            raise Exception(f"Sheet ids list '{sheet_ids_in_new_order}' contains duplicate sheet ids.")

        # Step 3: Get the original sheet ids.
        sheet_metadata = self.get_sheets_medatada_from_sheet(spreadsheet_id)
        original_sheet_ids = [sheet["properties"]["sheetId"] for sheet in sheet_metadata]

        # Step 4: Check that original sheet ids and new sheet ids are the same set.
        if set(original_sheet_ids) != set(sheet_ids_in_new_order):
            raise Exception(
                f"Original sheet ids '{original_sheet_ids}' and new sheet ids "
                f"'{sheet_ids_in_new_order}' are not the same."
            )

        requests = []
        for index, sheet_id in enumerate(sheet_ids_in_new_order):
            requests.append(
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "index": index,
                        },
                        "fields": "index",
                    }
                }
            )

        request_body = {"requests": requests}

        return self.batch_update_spreadsheet(spreadsheet_id, request_body)