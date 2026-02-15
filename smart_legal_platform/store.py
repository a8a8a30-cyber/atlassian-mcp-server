from __future__ import annotations

from dataclasses import dataclass, field

from smart_legal_platform.models import (
    Appointment,
    ESignatureRecord,
    Invoice,
    LegalCase,
    SecureMessage,
    Task,
    TimeEntry,
)


@dataclass
class InMemoryStore:
    cases: dict[str, LegalCase] = field(default_factory=dict)
    tasks: dict[str, list[Task]] = field(default_factory=dict)
    appointments: dict[str, list[Appointment]] = field(default_factory=dict)
    time_entries: dict[str, list[TimeEntry]] = field(default_factory=dict)
    invoices: dict[str, list[Invoice]] = field(default_factory=dict)
    messages: list[SecureMessage] = field(default_factory=list)
    signatures: list[ESignatureRecord] = field(default_factory=list)


store = InMemoryStore()

