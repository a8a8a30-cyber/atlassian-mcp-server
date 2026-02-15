from __future__ import annotations

from fastapi import APIRouter, Depends

from smart_legal_platform.models import (
    ESignatureRecord,
    ESignatureRequest,
    SecureMessage,
    SecureMessageCreate,
    SecureMessageView,
    User,
)
from smart_legal_platform.security import get_current_user, require_permission
from smart_legal_platform.services.communication_service import (
    create_esignature,
    list_esignatures,
    list_messages_for_user,
    send_secure_message,
)


router = APIRouter(prefix="/api/communications", tags=["communications"])


@router.post("/messages", response_model=SecureMessage)
def send_message(
    payload: SecureMessageCreate,
    _: User = Depends(require_permission("communications:write")),
) -> SecureMessage:
    return send_secure_message(payload)


@router.get("/messages/inbox", response_model=list[SecureMessageView])
def inbox(current_user: User = Depends(get_current_user)) -> list[SecureMessageView]:
    return list_messages_for_user(current_user.username)


@router.post("/esignatures", response_model=ESignatureRecord)
def sign(
    payload: ESignatureRequest,
    _: User = Depends(require_permission("communications:write")),
) -> ESignatureRecord:
    return create_esignature(payload)


@router.get("/esignatures/{case_id}", response_model=list[ESignatureRecord])
def signatures(
    case_id: str,
    _: User = Depends(require_permission("cases:read")),
) -> list[ESignatureRecord]:
    return list_esignatures(case_id)

