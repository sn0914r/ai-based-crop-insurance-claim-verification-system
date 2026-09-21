from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.modules.claims.claim_schema import SubmitClaimRequest, StandardResponse
from app.modules.claims.claim_service import claim_service

router = APIRouter(prefix="/api/claims", tags=["Claims"])

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    summary="Submit Claim & Run Visual Assessment"
)
def submit_claim(
    request: SubmitClaimRequest,
    db: Session = Depends(get_db)
):
    """
    Submits a new crop damage claim with an image, evaluates damage using MobileNetV2,
    stores records and audit logs in SQLite, and returns assessment results.
    """
    result = claim_service.process_new_claim(db, request)
    has_weather = bool(result.get("weatherAssessment"))
    has_satellite = bool(result.get("satelliteAssessment"))
    if has_weather and has_satellite:
        message = "Claim submitted and verified with multimodal vision, weather, and satellite evidence successfully."
    elif has_weather:
        message = "Claim submitted and verified with multimodal evidence successfully."
    else:
        message = "Claim submitted and visually assessed successfully."
    return StandardResponse(
        success=True,
        message=message,
        data=result
    )

@router.get(
    "/{claim_id}",
    response_model=StandardResponse,
    summary="Get Claim Details by ID"
)
def get_claim(
    claim_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves full claim details, visual assessment metrics, and audit trail logs by claim ID.
    """
    result = claim_service.get_claim_details(db, claim_id)
    return StandardResponse(
        success=True,
        message="Claim retrieved successfully.",
        data=result
    )

@router.get(
    "/{claim_id}/audit",
    response_model=StandardResponse,
    summary="Get Audit Trail by Claim ID"
)
def get_claim_audit_trail(
    claim_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the chronological audit trail events for a claim.
    """
    result = claim_service.get_claim_details(db, claim_id)
    return StandardResponse(
        success=True,
        message="Audit trail retrieved successfully.",
        data=result.get("auditLogs", [])
    )

@router.get(
    "",
    response_model=StandardResponse,
    summary="List All Claims"
)
def list_claims(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Limit for pagination"),
    db: Session = Depends(get_db)
):
    """
    Lists submitted claims with their status and latest assessment metrics.
    """
    result = claim_service.list_all_claims(db, skip=skip, limit=limit)
    return StandardResponse(
        success=True,
        message="Claims retrieved successfully.",
        data=result
    )

@router.delete(
    "",
    response_model=StandardResponse,
    summary="Clear All Historical Claims"
)
def clear_claims(
    db: Session = Depends(get_db)
):
    """
    Clears all claims, assessments, and audit logs.
    """
    deleted_count = claim_service.clear_all_claims(db)
    return StandardResponse(
        success=True,
        message=f"Successfully cleared {deleted_count} claim records.",
        data={"clearedCount": deleted_count}
    )

