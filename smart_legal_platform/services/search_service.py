from __future__ import annotations

import math
import re
from collections import Counter

from smart_legal_platform.data.legal_corpus import LEGAL_CORPUS
from smart_legal_platform.models import (
    OutcomePrediction,
    PrecedentLink,
    SearchRequest,
    SearchResponse,
    SearchResult,
)


WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in WORD_RE.findall(text)]


def _score(query_tokens: list[str], doc_tokens: list[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_count = Counter(doc_tokens)
    unique_q = set(query_tokens)
    tf = sum(doc_count[t] for t in unique_q)
    norm = math.sqrt(len(doc_tokens)) + 1.0
    return tf / norm


def search_legal_sources(request: SearchRequest) -> SearchResponse:
    query_tokens = _tokenize(request.query)
    ranked: list[SearchResult] = []
    for entry in LEGAL_CORPUS:
        doc_tokens = _tokenize(f"{entry['title']} {entry['summary']} {entry['text']}")
        score = _score(query_tokens, doc_tokens)
        if score <= 0:
            continue
        ranked.append(
            SearchResult(
                source_id=entry["id"],
                title=entry["title"],
                summary=entry["summary"],
                score=round(score, 4),
                citations=entry["citations"],
            )
        )
    ranked.sort(key=lambda result: result.score, reverse=True)
    top_results = ranked[: request.top_k]
    if top_results:
        answer = " ".join([result.summary for result in top_results[:3]])
    else:
        answer = "No direct match found. Consider refining the legal question."
    return SearchResponse(
        question=request.query,
        synthesized_answer=answer,
        results=top_results,
    )


def find_precedent_links(case_id: str, top_k: int = 5) -> list[PrecedentLink]:
    case = next((entry for entry in LEGAL_CORPUS if entry["id"] == case_id), None)
    if not case:
        return []

    origin_tokens = set(_tokenize(f"{case['text']} {case['summary']}"))
    links: list[PrecedentLink] = []
    for entry in LEGAL_CORPUS:
        if entry["id"] == case_id:
            continue
        target_tokens = set(_tokenize(f"{entry['text']} {entry['summary']}"))
        overlap = origin_tokens.intersection(target_tokens)
        citation_overlap = set(case["citations"]).intersection(set(entry["citations"]))
        score = (len(overlap) * 0.2) + (len(citation_overlap) * 1.5)
        if score <= 0:
            continue
        reason_parts = []
        if citation_overlap:
            reason_parts.append(f"Shared citations: {', '.join(sorted(citation_overlap))}")
        if overlap:
            reason_parts.append(f"Shared legal terms count: {len(overlap)}")
        links.append(
            PrecedentLink(
                case_id=case_id,
                related_case_id=entry["id"],
                relationship_score=round(score, 3),
                reason=" | ".join(reason_parts),
            )
        )
    links.sort(key=lambda item: item.relationship_score, reverse=True)
    return links[:top_k]


def predict_outcome(case_id: str) -> OutcomePrediction:
    case = next((entry for entry in LEGAL_CORPUS if entry["id"] == case_id), None)
    if not case:
        return OutcomePrediction(
            case_id=case_id,
            predicted_outcome="unknown",
            confidence=0.0,
            feature_contributions={"data_availability": 0.0},
        )

    strategy = case["strategy"]
    judge = case["judge"]
    same_strategy = [c for c in LEGAL_CORPUS if c["strategy"] == strategy]
    same_judge = [c for c in LEGAL_CORPUS if c["judge"] == judge]

    def win_rate(records: list[dict]) -> float:
        if not records:
            return 0.5
        wins = sum(1 for rec in records if rec["outcome"] == "win")
        partial = sum(1 for rec in records if rec["outcome"] == "partial")
        return (wins + 0.5 * partial) / len(records)

    strategy_rate = win_rate(same_strategy)
    judge_rate = win_rate(same_judge)
    citation_strength = min(len(case["citations"]) / 4.0, 1.0)
    final_score = (strategy_rate * 0.45) + (judge_rate * 0.35) + (citation_strength * 0.20)

    if final_score >= 0.66:
        predicted = "likely_win"
    elif final_score >= 0.45:
        predicted = "mixed_outcome"
    else:
        predicted = "likely_loss"

    return OutcomePrediction(
        case_id=case_id,
        predicted_outcome=predicted,
        confidence=round(final_score, 3),
        feature_contributions={
            "strategy_history": round(strategy_rate, 3),
            "judge_history": round(judge_rate, 3),
            "citation_strength": round(citation_strength, 3),
        },
    )

