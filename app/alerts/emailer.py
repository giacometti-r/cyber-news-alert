from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol


@dataclass(frozen=True)
class AlertEmail:
    subject: str
    body: str


class SmtpClient(Protocol):
    def send_message(self, msg: EmailMessage) -> None:
        ...


class Emailer:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        sender_email: str,
        recipient_email: str,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.sender_email = sender_email
        self.recipient_email = recipient_email

    def build_subject(self, victim_name: str, victim_category: str, attack_type: str) -> str:
        if victim_category == "company":
            return f"{victim_name} was attacked using {attack_type}"
        return f"[{victim_name}] was attacked using {attack_type}"

    def build_body(
        self,
        abstract: str,
        attack_type: str,
        victim_name: str,
        victim_category: str,
        source_name: str,
        published_date: str,
        link: str,
    ) -> str:
        return (
            f"Abstract:\n{abstract}\n\n"
            f"Attack type: {attack_type}\n"
            f"Victim: {victim_name}\n"
            f"Victim category: {victim_category}\n"
            f"Source: {source_name}\n"
            f"Published date: {published_date}\n"
            f"Article link: {link}\n"
        )

    def send(self, email: AlertEmail) -> None:
        message = EmailMessage()
        message["From"] = self.sender_email
        message["To"] = self.recipient_email
        message["Subject"] = email.subject
        message.set_content(email.body)

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(self.smtp_username, self.smtp_password)
            smtp.send_message(message)
