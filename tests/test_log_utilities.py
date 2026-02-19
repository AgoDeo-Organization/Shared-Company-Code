import logging
import logging.handlers
from pathlib import Path

import pytest

from julien_python_toolkit.log_utilities import DEBUG, INFO, WARNING, Logger


def _clear_logger(name: str) -> None:
    """Remove handlers from a logger so each test starts clean."""

    logger = logging.getLogger(name)

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def test_logger_creates_log_folder_and_expected_handlers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Logger should create a logs folder with stream and rotating file handlers."""

    logger_name = "test_logger_creates_log_folder_and_expected_handlers"
    _clear_logger(logger_name)

    monkeypatch.chdir(tmp_path)

    logger_wrapper = Logger(
        name=logger_name,
        file_name="application.log",
        stream_log_level=WARNING,
        file_log_level=INFO,
    )

    log_folder = tmp_path / "logs"

    assert log_folder.exists()
    assert log_folder.is_dir()

    handlers = logger_wrapper._logger.handlers

    stream_handler = next((h for h in handlers if type(h) is logging.StreamHandler), None)
    file_handler = next((h for h in handlers if isinstance(h, logging.handlers.RotatingFileHandler)), None)

    assert stream_handler is not None
    assert file_handler is not None
    assert stream_handler.level == WARNING
    assert file_handler.level == INFO
    assert (log_folder / "application.log").exists()

    _clear_logger(logger_name)


def test_logger_methods_write_expected_messages_to_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrapper methods should route messages to the underlying logger."""

    logger_name = "test_logger_methods_write_expected_messages_to_file"
    _clear_logger(logger_name)

    monkeypatch.chdir(tmp_path)

    logger_wrapper = Logger(
        name=logger_name,
        file_name="messages.log",
        stream_log_level=logging.CRITICAL,
        file_log_level=DEBUG,
    )

    logger_wrapper.debug("debug entry")
    logger_wrapper.info("info entry")
    logger_wrapper.warn("warn entry")
    logger_wrapper.warning("warning entry")
    logger_wrapper.error("error entry")

    for handler in logger_wrapper._logger.handlers:
        handler.flush()

    log_text = (tmp_path / "logs" / "messages.log").read_text(encoding="utf-8")

    assert "debug entry" in log_text
    assert "info entry" in log_text
    assert "warn entry" in log_text
    assert "warning entry" in log_text
    assert "error entry" in log_text

    _clear_logger(logger_name)


def test_set_file_and_stream_log_level_ignores_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Passing None should keep existing handler log levels unchanged."""

    logger_name = "test_set_file_and_stream_log_level_ignores_none"
    _clear_logger(logger_name)

    monkeypatch.chdir(tmp_path)

    logger_wrapper = Logger(
        name=logger_name,
        file_name="level.log",
        stream_log_level=WARNING,
        file_log_level=INFO,
    )

    stream_handler = next(
        h for h in logger_wrapper._logger.handlers if type(h) is logging.StreamHandler
    )
    file_handler = next(
        h
        for h in logger_wrapper._logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    )

    old_stream_level = stream_handler.level
    old_file_level = file_handler.level

    logger_wrapper.set_stream_log_level(None)
    logger_wrapper.set_file_log_level(None)

    assert stream_handler.level == old_stream_level
    assert file_handler.level == old_file_level

    _clear_logger(logger_name)


def test_logger_raises_for_missing_parent_folder_in_file_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Creating a logger with a nested missing file path should fail explicitly."""

    logger_name = "test_logger_raises_for_missing_parent_folder_in_file_name"
    _clear_logger(logger_name)

    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError):
        Logger(
            name=logger_name,
            file_name="missing/subfolder/app.log",
            stream_log_level=WARNING,
            file_log_level=INFO,
        )

    _clear_logger(logger_name)
