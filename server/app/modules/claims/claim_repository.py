from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.models import Claim, ClaimAssessment, AuditLog

class ClaimRepository:
    """
    Data access layer for claims, assessments, and audit logs.
    """
    @staticmethod
    def create_claim(db: Session, claim: Claim) -> Claim:
        db.add(claim)
        db.commit()
        db.refresh(claim)
        return claim

    @staticmethod
    def get_claim_by_id(db: Session, claim_id: str) -> Optional[Claim]:
        return db.query(Claim).filter(Claim.claim_id == claim_id).first()

    @staticmethod
    def list_claims(db: Session, skip: int = 0, limit: int = 50) -> List[Claim]:
        return db.query(Claim).order_by(Claim.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_claim_status(db: Session, claim_id: str, status: str, image_path: Optional[str] = None) -> Optional[Claim]:
        claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
        if claim:
            claim.status = status
            if image_path:
                claim.image_path = image_path
            db.commit()
            db.refresh(claim)
        return claim

    @staticmethod
    def save_assessment(db: Session, assessment: ClaimAssessment) -> ClaimAssessment:
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def get_latest_assessment(db: Session, claim_id: str) -> Optional[ClaimAssessment]:
        return db.query(ClaimAssessment).filter(ClaimAssessment.claim_id == claim_id).order_by(ClaimAssessment.created_at.desc()).first()

    @staticmethod
    def create_audit_log(db: Session, audit_log: AuditLog) -> AuditLog:
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log

claim_repository = ClaimRepository()
