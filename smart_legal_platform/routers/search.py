from __future__ import annotations

from fastapi import APIRouter, Depends

from smart_legal_platform.models import OutcomePrediction, PrecedentLink, SearchRequest, SearchResponse, User
from smart_legal_platform.security import require_permission
from smart_legal_platform.services.search_service import (
    find_precedent_links,
    predict_outcome,
    search_legal_sources,
)


router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/query", response_model=SearchResponse)
def query_sources(
    payload: SearchRequest,
    _: User = Depends(require_permission("search:read")),
) -> SearchResponse:
    return search_legal_sources(payload)


@router.get("/precedents/{case_id}/links", response_model=list[PrecedentLink])
def precedent_links(
    case_id: str,
    _: User = Depends(require_permission("search:read")),
) -> list[PrecedentLink]:
    return find_precedent_links(case_id)


@router.get("/outcome-prediction/{case_id}", response_model=OutcomePrediction)
def outcome_prediction(
    case_id: str,
    _: User = Depends(require_permission("search:read")),
) -> OutcomePrediction:
    return predict_outcome(case_id)

