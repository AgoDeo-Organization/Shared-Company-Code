# This file is part of the "your-package-name" project.
# It is licensed under the "Custom Non-Commercial License".
# You may not use this file for commercial purposes without
# explicit permission from the author.


import datetime
import time
from typing import Protocol


class _SupportsEmailSend(Protocol):
    def send_emails(self, subject: str, body: str) -> None:
        """Send an email payload to one or many recipients.

        Args:
            subject: Subject line used for the outgoing email.
            body: Message body that should be sent.
        """


class EmailLogger:
    """Collect log lines and send them by email in one batch."""

    def __init__(
        self,
        email_sender: _SupportsEmailSend,
        logger_name: str,
        subject: str,
        timestamp: bool = True,
    ) -> None:
        """Create a logger that stores messages until ``send`` is called.

        Args:
            email_sender: Object that can send emails.
            logger_name: Name to show inside each formatted log line.
            subject: Subject line to use when sending buffered logs.
            timestamp: If ``True``, prepend timestamps to buffered log lines.
        """

        self.email_sender = email_sender
        self.logger_name = logger_name
        self.subject = subject
        self.timestamp = timestamp
        self.buffer: list[str] = []

    def critical(self, message: str) -> None:
        """Add a CRITICAL log message to the email buffer.

        Args:
            message: Log message text to store.
        """

        self._log_message(message, "CRITICAL")

    def error(self, message: str) -> None:
        """Add an ERROR log message to the email buffer.

        Args:
            message: Log message text to store.
        """

        self._log_message(message, "ERROR")

    def warning(self, message: str) -> None:
        """Add a WARNING log message to the email buffer.

        Args:
            message: Log message text to store.
        """

        self._log_message(message, "WARNING")

    def info(self, message: str) -> None:
        """Add an INFO log message to the email buffer.

        Args:
            message: Log message text to store.
        """

        self._log_message(message, "INFO")

    def debug(self, message: str) -> None:
        """Add a DEBUG log message to the email buffer.

        Args:
            message: Log message text to store.
        """

        self._log_message(message, "DEBUG")

    def _log_message(self, message: str, log_level: str = "INFO") -> None:
        """Format one message and append it to the internal buffer."""

        formatted_message = ""

        if self.timestamp:
            formatted_message += f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - "

        formatted_message += f"{log_level} - {self.logger_name} - {message}"

        self.buffer.append(formatted_message)

    def send(self) -> None:
        """Send all buffered log lines as one email and clear the buffer.

        This method does nothing when the buffer is empty.
        """

        if self.buffer:
            log_message = "\n".join(self.buffer)
            self.email_sender.send_emails(self.subject, log_message)
            self.buffer = []


class TimedEmailLogger(EmailLogger):
    """Email logger that auto-sends buffered logs on a time interval."""

    def __init__(
        self,
        email_sender: _SupportsEmailSend,
        logger_name: str,
        subject: str,
        timestamp: bool = True,
        interval: int = 60,
    ) -> None:
        """Create a timed logger with an interval in seconds.

        Args:
            email_sender: Object that can send emails.
            logger_name: Name to show inside each formatted log line.
            subject: Subject line to use when sending buffered logs.
            timestamp: If ``True``, prepend timestamps to buffered log lines.
            interval: Number of seconds to wait between automatic sends.
        """

        super().__init__(email_sender, logger_name, subject, timestamp=timestamp)
        self.interval = interval
        self.last_email_time = time.time()

    def _log_message(self, message: str, log_level: str = "INFO") -> None:
        """Append a message and send if the interval has elapsed."""

        super()._log_message(message, log_level)

        current_time = time.time()

        if current_time - self.last_email_time >= self.interval:
            self.send()
            self.last_email_time = current_time
