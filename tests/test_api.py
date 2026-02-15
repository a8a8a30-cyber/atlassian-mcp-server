from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from smart_legal_platform.main import app


client = TestClient(app)


def get_token(username: str, password: str) -> str:
    response = client.post(
        "/api/auth/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(username: str, password: str) -> dict[str, str]:
    token = get_token(username, password)
    return {"Authorization": f"Bearer {token}"}


def test_healthcheck() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_and_prediction() -> None:
    headers = auth_header("nora", "Lawyer@123")
    search_response = client.post(
        "/api/search/query",
        json={"query": "payment delay and termination notice", "top_k": 3},
        headers=headers,
    )
    assert search_response.status_code == 200
    body = search_response.json()
    assert len(body["results"]) >= 1
    assert "question" in body

    prediction_response = client.get(
        "/api/search/outcome-prediction/C-1001",
        headers=headers,
    )
    assert prediction_response.status_code == 200
    assert prediction_response.json()["predicted_outcome"] in {
        "likely_win",
        "mixed_outcome",
        "likely_loss",
    }


def test_contract_analysis_and_generation() -> None:
    headers = auth_header("omar", "Lawyer@123")
    contract_text = """
    This agreement includes payment due within 10 days from invoice date.
    Either party may request termination without notice at sole discretion.
    The supplier accepts unlimited liability for all indirect damages.
    Any dispute shall be subject to exclusive jurisdiction in a foreign court.
    """
    analysis_response = client.post(
        "/api/contracts/analyze",
        json={"contract_text": contract_text},
        headers=headers,
    )
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()
    assert "payment_terms" in analysis["extracted_clauses"]
    assert len(analysis["risks"]) >= 1

    document_response = client.post(
        "/api/contracts/generate-document",
        json={
            "template_name": "nda",
            "fields": {
                "party_a": "Firm A",
                "party_b": "Client B",
                "effective_date": "2026-02-15",
                "purpose": "case strategy collaboration",
                "term": "3 years",
                "governing_law": "Saudi law",
            },
        },
        headers=headers,
    )
    assert document_response.status_code == 200
    assert "NON-DISCLOSURE AGREEMENT" in document_response.json()["document"]


def test_case_management_communications_analytics_and_backup() -> None:
    lawyer_headers = auth_header("nora", "Lawyer@123")
    case_response = client.post(
        "/api/cases",
        json={
            "title": "Client Alpha v. Vendor Z",
            "client_name": "Client Alpha",
            "judge": "Judge Faris",
            "strategy": "strict_enforcement",
            "value_at_risk": 250000,
        },
        headers=lawyer_headers,
    )
    assert case_response.status_code == 200
    case_id = case_response.json()["id"]

    task_response = client.post(
        f"/api/cases/{case_id}/tasks",
        json={
            "title": "Prepare claim memo",
            "assignee": "nora",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        },
        headers=lawyer_headers,
    )
    assert task_response.status_code == 200

    time_response = client.post(
        f"/api/cases/{case_id}/time-entries",
        json={"user": "nora", "hours": 4.5, "rate": 150, "description": "Research and drafting"},
        headers=lawyer_headers,
    )
    assert time_response.status_code == 200

    invoice_response = client.post(
        f"/api/cases/{case_id}/invoices",
        json={"issued_to": "Client Alpha", "tax_percent": 15},
        headers=lawyer_headers,
    )
    assert invoice_response.status_code == 200
    assert invoice_response.json()["total"] > 0

    message_response = client.post(
        "/api/communications/messages",
        json={
            "sender": "nora",
            "recipient": "client1",
            "subject": "Case update",
            "body": "We have completed the first contract risk review.",
            "case_id": case_id,
        },
        headers=lawyer_headers,
    )
    assert message_response.status_code == 200
    assert "encrypted_body" in message_response.json()

    client_headers = auth_header("client1", "Client@123")
    inbox_response = client.get("/api/communications/messages/inbox", headers=client_headers)
    assert inbox_response.status_code == 200
    assert len(inbox_response.json()) >= 1
    assert "contract risk review" in inbox_response.json()[0]["body"].lower()

    dashboard_response = client.get("/api/analytics/dashboard", headers=lawyer_headers)
    assert dashboard_response.status_code == 200
    assert "total_cases" in dashboard_response.json()

    signals_response = client.get(f"/api/analytics/signals/{case_id}", headers=lawyer_headers)
    assert signals_response.status_code == 200
    assert signals_response.json()["risk_score"] >= 0

    admin_headers = auth_header("admin", "Admin@12345")
    backup_response = client.post("/api/security/backup", headers=admin_headers)
    assert backup_response.status_code == 200
    assert backup_response.json()["backup_path"].endswith(".json.enc")
