from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from smart_legal_platform.models import (
    Appointment,
    AppointmentCreate,
    Invoice,
    InvoiceCreate,
    LegalCase,
    LegalCaseCreate,
    Task,
    TaskCreate,
    TimeEntry,
    TimeEntryCreate,
)
from smart_legal_platform.security import random_token
from smart_legal_platform.store import store


def create_case(payload: LegalCaseCreate) -> LegalCase:
    now = datetime.now(timezone.utc)
    case = LegalCase(
        id=random_token("case"),
        title=payload.title,
        client_name=payload.client_name,
        judge=payload.judge,
        strategy=payload.strategy,
        value_at_risk=payload.value_at_risk,
        created_at=now,
        updated_at=now,
    )
    store.cases[case.id] = case
    return case


def get_case(case_id: str) -> LegalCase:
    case = store.cases.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    return case


def list_cases() -> list[LegalCase]:
    return sorted(store.cases.values(), key=lambda case: case.created_at, reverse=True)


def create_task(case_id: str, payload: TaskCreate) -> Task:
    get_case(case_id)
    task = Task(
        id=random_token("task"),
        case_id=case_id,
        title=payload.title,
        assignee=payload.assignee,
        due_date=payload.due_date,
    )
    store.tasks.setdefault(case_id, []).append(task)
    return task


def list_tasks(case_id: str) -> list[Task]:
    get_case(case_id)
    return store.tasks.get(case_id, [])


def create_appointment(case_id: str, payload: AppointmentCreate) -> Appointment:
    get_case(case_id)
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=400, detail="Appointment end must be after start")
    appointment = Appointment(
        id=random_token("appt"),
        case_id=case_id,
        title=payload.title,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        participants=payload.participants,
    )
    store.appointments.setdefault(case_id, []).append(appointment)
    return appointment


def list_appointments(case_id: str) -> list[Appointment]:
    get_case(case_id)
    return store.appointments.get(case_id, [])


def create_time_entry(case_id: str, payload: TimeEntryCreate) -> TimeEntry:
    get_case(case_id)
    entry = TimeEntry(
        id=random_token("time"),
        case_id=case_id,
        user=payload.user,
        hours=payload.hours,
        rate=payload.rate,
        description=payload.description,
        created_at=datetime.now(timezone.utc),
    )
    store.time_entries.setdefault(case_id, []).append(entry)
    return entry


def list_time_entries(case_id: str) -> list[TimeEntry]:
    get_case(case_id)
    return store.time_entries.get(case_id, [])


def create_invoice(case_id: str, payload: InvoiceCreate) -> Invoice:
    get_case(case_id)
    entries = store.time_entries.get(case_id, [])
    subtotal = sum(entry.hours * entry.rate for entry in entries)
    total = subtotal * (1 + payload.tax_percent / 100)
    invoice = Invoice(
        id=random_token("inv"),
        case_id=case_id,
        issued_to=payload.issued_to,
        subtotal=round(subtotal, 2),
        tax_percent=payload.tax_percent,
        total=round(total, 2),
        created_at=datetime.now(timezone.utc),
    )
    store.invoices.setdefault(case_id, []).append(invoice)
    return invoice


def list_invoices(case_id: str) -> list[Invoice]:
    get_case(case_id)
    return store.invoices.get(case_id, [])

