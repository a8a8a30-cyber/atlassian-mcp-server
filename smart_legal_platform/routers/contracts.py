from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from smart_legal_platform.models import (
    ContractAnalysisResponse,
    ContractGenerateRequest,
    ContractReviewRequest,
    User,
)
from smart_legal_platform.security import require_permission
from smart_legal_platform.services.contract_service import (
    analyze_contract,
    extract_clauses,
    generate_legal_document,
)


router = APIRouter(prefix="/api/contracts", tags=["contracts"])


@router.post("/analyze", response_model=ContractAnalysisResponse)
def analyze(
    payload: ContractReviewRequest,
    _: User = Depends(require_permission("contracts:analyze")),
) -> ContractAnalysisResponse:
    return analyze_contract(payload)


@router.post("/extract-clauses", response_model=dict[str, str])
def extract(
    payload: ContractReviewRequest,
    _: User = Depends(require_permission("contracts:analyze")),
) -> dict[str, str]:
    return extract_clauses(payload.contract_text)


@router.post("/generate-document")
def generate_document(
    payload: ContractGenerateRequest,
    _: User = Depends(require_permission("contracts:analyze")),
) -> dict[str, str]:
    try:
        document = generate_legal_document(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"document": document}

