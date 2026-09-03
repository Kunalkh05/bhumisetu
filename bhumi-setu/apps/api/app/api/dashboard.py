"""Officer dashboard endpoints."""

from __future__ import annotations

from fastapi import Depends

from app.api.cases import _read_session
from app.api.routers import officer_router
from app.schemas.dashboard import DashboardMetricOut, DashboardOut
from app.security.access import Principal, authenticate
from app.services.dashboard import dashboard_response

__all__ = []


@officer_router.get("/dashboard", response_model=DashboardOut)
def dashboard(principal: Principal = Depends(authenticate)) -> DashboardOut:
    with _read_session() as session:
        response = dashboard_response(session, principal=principal)
        return DashboardOut(
            metrics={
                key: DashboardMetricOut(**metric.to_json())
                for key, metric in response.metrics.items()
            }
        )
