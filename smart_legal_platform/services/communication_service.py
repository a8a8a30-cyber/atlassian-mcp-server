from __future__ import annotations

from hashlib import sha256

from smart_legal_platform.models import (
    ESignatureRecord,
    ESignatureRequest,
    SecureMessage,
    SecureMessageCreate,
    SecureMessageView,
)
from smart_legal_platform.security import decrypt_text, encrypt_text, random_token
from smart_legal_platform.store import store


def send_secure_message(payload: SecureMessageCreate) -> SecureMessage:
    encrypted_body = encrypt_text(payload.body)
    message = SecureMessage(
        id=random_token("msg"),
        sender=payload.sender,
        recipient=payload.recipient,
        subject=payload.subject,
        encrypted_body=encrypted_body,
        case_id=payload.case_id,
    )
    store.messages.append(message)
    return message


def list_messages_for_user(username: str) -> list[SecureMessageView]:
    views: list[SecureMessageView] = []
    for message in store.messages:
        if message.recipient != username and message.sender != username:
            continue
        views.append(
            SecureMessageView(
                id=message.id,
                sender=message.sender,
                recipient=message.recipient,
                subject=message.subject,
                body=decrypt_text(message.encrypted_body),
                case_id=message.case_id,
                created_at=message.created_at,
            )
        )
    return sorted(views, key=lambda item: item.created_at, reverse=True)


def create_esignature(payload: ESignatureRequest) -> ESignatureRecord:
    raw = f"{payload.case_id}|{payload.signer}|{payload.document_hash}|{payload.signed_at.isoformat()}"
    verification_code = sha256(raw.encode("utf-8")).hexdigest()[:20]
    record = ESignatureRecord(
        id=random_token("sig"),
        case_id=payload.case_id,
        signer=payload.signer,
        document_hash=payload.document_hash,
        signed_at=payload.signed_at,
        verification_code=verification_code,
    )
    store.signatures.append(record)
    return record


def list_esignatures(case_id: str) -> list[ESignatureRecord]:
    return [record for record in store.signatures if record.case_id == case_id]

