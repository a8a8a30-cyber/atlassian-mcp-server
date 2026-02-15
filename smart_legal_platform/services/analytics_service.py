from __future__ import annotations

from collections import defaultdict

from smart_legal_platform.data.legal_corpus import LEGAL_CORPUS
from smart_legal_platform.models import (
    DashboardMetrics,
    RiskOpportunitySignal,
    StrategyPrediction,
)
from smart_legal_platform.store import store


def dashboard_metrics() -> DashboardMetrics:
    cases = list(store.cases.values())
    entries = [entry for case_entries in store.time_entries.values() for entry in case_entries]

    total_cases = len(cases)
    active_cases = sum(1 for case in cases if case.status in {"active", "trial", "negotiation"})
    avg_hours = round(sum(entry.hours for entry in entries) / total_cases, 2) if total_cases else 0.0
    revenue = round(sum(entry.hours * entry.rate for entry in entries), 2)

    lawyer_bucket: dict[str, list[float]] = defaultdict(list)
    judge_bucket: dict[str, list[float]] = defaultdict(list)
    for record in LEGAL_CORPUS:
        score = 1.0 if record["outcome"] == "win" else 0.5 if record["outcome"] == "partial" else 0.0
        lawyer_bucket[record["lawyer"]].append(score)
        judge_bucket[record["judge"]].append(score)

    lawyer_success_rate = {
        lawyer: round(sum(scores) / len(scores), 3) for lawyer, scores in lawyer_bucket.items()
    }
    judge_trend_score = {
        judge: round(sum(scores) / len(scores), 3) for judge, scores in judge_bucket.items()
    }

    return DashboardMetrics(
        total_cases=total_cases,
        active_cases=active_cases,
        avg_hours_per_case=avg_hours,
        revenue_estimate=revenue,
        lawyer_success_rate=lawyer_success_rate,
        judge_trend_score=judge_trend_score,
    )


def predict_strategy(strategy: str) -> StrategyPrediction:
    records = [case for case in LEGAL_CORPUS if case["strategy"] == strategy]
    if not records:
        return StrategyPrediction(strategy=strategy, probability_of_success=0.5, sample_size=0)
    wins = sum(1 for case in records if case["outcome"] == "win")
    partial = sum(1 for case in records if case["outcome"] == "partial")
    probability = (wins + 0.5 * partial) / len(records)
    return StrategyPrediction(
        strategy=strategy,
        probability_of_success=round(probability, 3),
        sample_size=len(records),
    )


def risk_opportunity_for_case(case_id: str) -> RiskOpportunitySignal:
    case = store.cases.get(case_id)
    if not case:
        return RiskOpportunitySignal(
            case_id=case_id,
            risk_score=0.0,
            opportunity_score=0.0,
            drivers=["Case not found in active workspace"],
        )

    strategy_prediction = predict_strategy(case.strategy)
    value_factor = min(case.value_at_risk / 1_000_000, 1.0)
    risk_score = round((1 - strategy_prediction.probability_of_success) * 0.7 + value_factor * 0.3, 3)
    opportunity_score = round((strategy_prediction.probability_of_success * 0.7) + (1 - value_factor) * 0.3, 3)

    drivers = [
        f"Strategy success probability: {strategy_prediction.probability_of_success}",
        f"Value at risk factor: {round(value_factor, 3)}",
    ]

    return RiskOpportunitySignal(
        case_id=case_id,
        risk_score=risk_score,
        opportunity_score=opportunity_score,
        drivers=drivers,
    )

