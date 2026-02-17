"""Unit tests for SMTP email sender."""

from __future__ import annotations

from unittest.mock import Mock

from julien_python_toolkit.src import email_sender



def _build_sender(monkeypatch) -> email_sender.EmailSender:
    """Create a sender without opening a real SMTP connection."""

    monkeypatch.setattr(email_sender.EmailSender, "_connect_and_login", lambda self: None)
    return email_sender.EmailSender(
        sender_email="sender@example.com",
        sender_password="pwd",
        receiver_emails=["a@example.com", "b@example.com"],
    )



def test_send_emails_calls_private_send_for_each_receiver(monkeypatch) -> None:
    """send_emails should loop through all configured recipients."""

    sender = _build_sender(monkeypatch)
    sender._send_email = Mock()

    sender.send_emails("hello", "body")

    assert sender._send_email.call_count == 2
    sender._send_email.assert_any_call("a@example.com", "hello", "body")
    sender._send_email.assert_any_call("b@example.com", "hello", "body")



def test_reconnect_if_needed_reconnects_on_unhealthy_connection(monkeypatch) -> None:
    """Unhealthy SMTP status should trigger reconnect logic."""

    sender = _build_sender(monkeypatch)
    sender._smtp = Mock()
    sender._smtp.noop.return_value = (500, b"bad")
    sender._connect_and_login = Mock()

    sender._reconnect_if_needed()

    sender._connect_and_login.assert_called_once_with()



def test_send_email_delivers_message(monkeypatch) -> None:
    """_send_email should pass a populated EmailMessage to SMTP."""

    sender = _build_sender(monkeypatch)
    sender._reconnect_if_needed = Mock()
    sender._smtp = Mock()

    sender._send_email("rcpt@example.com", "Subject", "Body")

    sender._smtp.send_message.assert_called_once()
    sent_message = sender._smtp.send_message.call_args.args[0]

    assert sent_message["From"] == "sender@example.com"
    assert sent_message["To"] == "rcpt@example.com"
    assert sent_message["Subject"] == "Subject"
    assert "Body" in sent_message.get_content()



def test_send_email_logs_error_when_smtp_is_missing(monkeypatch) -> None:
    """Missing SMTP connection should be handled and logged as an error."""

    sender = _build_sender(monkeypatch)
    sender._reconnect_if_needed = Mock()
    sender._smtp = None

    error_mock = Mock()
    monkeypatch.setattr(email_sender.logger, "error", error_mock)

    sender._send_email("rcpt@example.com", "Subject", "Body")

    assert error_mock.call_count == 1
    assert "SMTP connection is not initialized" in error_mock.call_args.args[0]
