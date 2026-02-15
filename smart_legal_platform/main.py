from __future__ import annotations

from fastapi import FastAPI

from smart_legal_platform.config import get_settings
from smart_legal_platform.routers import (
    analytics,
    auth,
    cases,
    communications,
    contracts,
    health,
    search,
    security_ops,
)


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Unified legal operations platform with AI-powered search, "
        "contract intelligence, case management, analytics, and security controls."
    ),
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(contracts.router)
app.include_router(cases.router)
app.include_router(communications.router)
app.include_router(analytics.router)
app.include_router(security_ops.router)

