from __future__ import annotations

from fastapi import APIRouter, Depends

from smart_legal_platform.models import DashboardMetrics, RiskOpportunitySignal, StrategyPrediction, User
from smart_legal_platform.security import require_permission
from smart_legal_platform.services.analytics_service import (
    dashboard_metrics,
    predict_strategy,
    risk_opportunity_for_case,
)


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardMetrics)
def dashboard(_: User = Depends(require_permission("analytics:read"))) -> DashboardMetrics:
    return dashboard_metrics()


@router.get("/strategies/{strategy}", response_model=StrategyPrediction)
def strategy(strategy: str, _: User = Depends(require_permission("analytics:read"))) -> StrategyPrediction:
    return predict_strategy(strategy)


@router.get("/signals/{case_id}", response_model=RiskOpportunitySignal)
def case_signals(
    case_id: str,
    _: User = Depends(require_permission("analytics:read")),
) -> RiskOpportunitySignal:
    return risk_opportunity_for_case(case_id)

