from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.audit.service import AuditService
from app.auth.dependencies import SessionDependency

router = APIRouter(tags=["Auditoria pública"])


@router.get("/lots/{lot_id}/audit")
def audit(
    lot_id: UUID,
    session: SessionDependency,
    response: Response,
    after: int = Query(0, ge=0),
):
    # One consistent read, without blocking accepted bids for the full scan.
    session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    response.headers["Cache-Control"] = "no-store"
    return AuditService(session).verify(lot_id, after=after)
