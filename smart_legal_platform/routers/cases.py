from __future__ import annotations

from fastapi import APIRouter, Depends

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
    User,
)
from smart_legal_platform.security import require_permission
from smart_legal_platform.services.case_management_service import (
    create_appointment,
    create_case,
    create_invoice,
    create_task,
    create_time_entry,
    get_case,
    list_appointments,
    list_cases,
    list_invoices,
    list_tasks,
    list_time_entries,
)


router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("", response_model=LegalCase)
def new_case(
    payload: LegalCaseCreate,
    _: User = Depends(require_permission("cases:write")),
) -> LegalCase:
    return create_case(payload)


@router.get("", response_model=list[LegalCase])
def cases(_: User = Depends(require_permission("cases:read"))) -> list[LegalCase]:
    return list_cases()


@router.get("/{case_id}", response_model=LegalCase)
def case_by_id(
    case_id: str,
    _: User = Depends(require_permission("cases:read")),
) -> LegalCase:
    return get_case(case_id)


@router.post("/{case_id}/tasks", response_model=Task)
def add_task(
    case_id: str,
    payload: TaskCreate,
    _: User = Depends(require_permission("cases:write")),
) -> Task:
    return create_task(case_id, payload)


@router.get("/{case_id}/tasks", response_model=list[Task])
def tasks(
    case_id: str,
    _: User = Depends(require_permission("cases:read")),
) -> list[Task]:
    return list_tasks(case_id)


@router.post("/{case_id}/appointments", response_model=Appointment)
def add_appointment(
    case_id: str,
    payload: AppointmentCreate,
    _: User = Depends(require_permission("cases:write")),
) -> Appointment:
    return create_appointment(case_id, payload)


@router.get("/{case_id}/appointments", response_model=list[Appointment])
def appointments(
    case_id: str,
    _: User = Depends(require_permission("cases:read")),
) -> list[Appointment]:
    return list_appointments(case_id)


@router.post("/{case_id}/time-entries", response_model=TimeEntry)
def add_time_entry(
    case_id: str,
    payload: TimeEntryCreate,
    _: User = Depends(require_permission("cases:write")),
) -> TimeEntry:
    return create_time_entry(case_id, payload)


@router.get("/{case_id}/time-entries", response_model=list[TimeEntry])
def time_entries(
    case_id: str,
    _: User = Depends(require_permission("cases:read")),
) -> list[TimeEntry]:
    return list_time_entries(case_id)


@router.post("/{case_id}/invoices", response_model=Invoice)
def add_invoice(
    case_id: str,
    payload: InvoiceCreate,
    _: User = Depends(require_permission("cases:write")),
) -> Invoice:
    return create_invoice(case_id, payload)


@router.get("/{case_id}/invoices", response_model=list[Invoice])
def invoices(
    case_id: str,
    _: User = Depends(require_permission("cases:read")),
) -> list[Invoice]:
    return list_invoices(case_id)

