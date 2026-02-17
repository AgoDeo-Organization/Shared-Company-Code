"""Unit tests for email logger helpers."""

from __future__ import annotations

from unittest.mock import Mock

from julien_python_toolkit import email_logger



def test_email_logger_adds_level_prefix_without_timestamp() -> None:
    """EmailLogger should format lines with level and logger name."""

    sender = Mock()
    logger = email_logger.EmailLogger(
        email_sender=sender,
        logger_name="worker",
        subject="subject",
        timestamp=False,
    )

    logger.warning("disk is almost full")

    assert logger.buffer == ["WARNING - worker - disk is almost full"]



def test_email_logger_send_sends_once_and_clears_buffer() -> None:
    """Sending should flush all buffered lines in one email payload."""

    sender = Mock()
    logger = email_logger.EmailLogger(sender, "worker", "daily", timestamp=False)

    logger.info("started")
    logger.error("failed")

    logger.send()

    sender.send_emails.assert_called_once_with("daily", "INFO - worker - started\nERROR - worker - failed")
    assert logger.buffer == []



def test_email_logger_send_with_empty_buffer_does_nothing() -> None:
    """Sending with no buffered rows should not call email sender."""

    sender = Mock()
    logger = email_logger.EmailLogger(sender, "worker", "daily")

    logger.send()

    sender.send_emails.assert_not_called()



def test_timed_email_logger_sends_when_interval_elapsed(monkeypatch) -> None:
    """TimedEmailLogger should auto-send once the interval has passed."""

    fake_times = iter([0.0, 10.0])
    monkeypatch.setattr(email_logger.time, "time", lambda: next(fake_times))

    sender = Mock()
    logger = email_logger.TimedEmailLogger(
        email_sender=sender,
        logger_name="worker",
        subject="daily",
        timestamp=False,
        interval=5,
    )

    logger.info("tick")

    sender.send_emails.assert_called_once_with("daily", "INFO - worker - tick")
    assert logger.buffer == []
