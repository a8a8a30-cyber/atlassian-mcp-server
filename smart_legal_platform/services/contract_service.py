from __future__ import annotations

import re

from smart_legal_platform.models import (
    ContractAnalysisResponse,
    ContractGenerateRequest,
    ContractRisk,
    ContractReviewRequest,
)


CLAUSE_PATTERNS = {
    "payment_terms": r"(payment|fees?|invoices?|installments?).{0,220}",
    "termination": r"(termination|terminate|cancellation|cancel).{0,220}",
    "confidentiality": r"(confidential|non-disclosure|nda|trade secret).{0,220}",
    "liability": r"(liability|indemnif|damages|penalty).{0,220}",
    "dispute_resolution": r"(arbitration|jurisdiction|dispute|governing law).{0,220}",
}


RISK_PATTERNS: list[tuple[str, str, str, str]] = [
    (
        "liability",
        "high",
        r"(unlimited liability|without limitation of liability)",
        "Unlimited liability can expose the client to extreme financial risk.",
    ),
    (
        "termination",
        "medium",
        r"(termination without notice|immediate termination at sole discretion)",
        "Unilateral termination may create execution and revenue uncertainty.",
    ),
    (
        "payment_terms",
        "high",
        r"(interest rate.{0,30}(2[0-9]|[3-9][0-9])\s*%)",
        "Very high late-payment interest can be commercially unacceptable.",
    ),
    (
        "dispute_resolution",
        "medium",
        r"(exclusive jurisdiction.{0,50}foreign court)",
        "Foreign exclusive jurisdiction may increase litigation cost and complexity.",
    ),
    (
        "renewal",
        "medium",
        r"(automatic renewal.{0,40}(5|6|7|8|9|10)\s*years?)",
        "Long auto-renewal periods reduce renegotiation flexibility.",
    ),
]


TEMPLATES = {
    "nda": (
        "NON-DISCLOSURE AGREEMENT\n\n"
        "This NDA is made between {party_a} and {party_b} on {effective_date}.\n"
        "Confidential information exchanged for {purpose} must be protected for {term}.\n"
        "Disputes are resolved under {governing_law}."
    ),
    "service_agreement": (
        "SERVICE AGREEMENT\n\n"
        "Provider: {provider}\nClient: {client}\nScope: {scope}\n"
        "Payment Terms: {payment_terms}\nTermination: {termination_terms}\n"
        "Governing Law: {governing_law}"
    ),
}


def extract_clauses(contract_text: str) -> dict[str, str]:
    extracted: dict[str, str] = {}
    for clause_name, pattern in CLAUSE_PATTERNS.items():
        match = re.search(pattern, contract_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            extracted[clause_name] = " ".join(match.group(0).split())
    return extracted


def detect_unusual_clauses(contract_text: str) -> list[str]:
    unusual = []
    normalized = contract_text.lower()
    if "sole discretion" in normalized and "termination" in normalized:
        unusual.append("High unilateral discretion around termination detected.")
    if "without prior notice" in normalized:
        unusual.append("No-notice action clause detected.")
    if "perpetual" in normalized:
        unusual.append("Perpetual obligation detected.")
    return unusual


def detect_risks(contract_text: str) -> list[ContractRisk]:
    risks: list[ContractRisk] = []
    for clause_type, severity, pattern, details in RISK_PATTERNS:
        if re.search(pattern, contract_text, flags=re.IGNORECASE | re.DOTALL):
            risks.append(
                ContractRisk(
                    clause_type=clause_type,
                    severity=severity,
                    details=details,
                )
            )
    return risks


def analyze_contract(request: ContractReviewRequest) -> ContractAnalysisResponse:
    clauses = extract_clauses(request.contract_text)
    unusual = detect_unusual_clauses(request.contract_text)
    risks = detect_risks(request.contract_text)
    return ContractAnalysisResponse(
        extracted_clauses=clauses,
        unusual_clauses=unusual,
        risks=risks,
    )


def generate_legal_document(request: ContractGenerateRequest) -> str:
    template = TEMPLATES.get(request.template_name.lower())
    if not template:
        available = ", ".join(sorted(TEMPLATES))
        raise ValueError(f"Unknown template '{request.template_name}'. Available: {available}")
    return template.format_map(DefaultDict(request.fields))


class DefaultDict(dict):
    def __missing__(self, key: str) -> str:
        return f"<{key}>"

