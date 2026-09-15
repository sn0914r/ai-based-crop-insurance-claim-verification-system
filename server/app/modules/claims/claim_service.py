import json
import time
import random
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.db.models import Claim, ClaimAssessment, AuditLog
from app.modules.claims.claim_repository import claim_repository
from app.modules.claims.claim_schema import SubmitClaimRequest
from app.providers.ml_provider import ml_provider
from app.errors.app_error import AppError
import app.errors.error_codes as error_codes

class ClaimService:
    """
    Business service orchestrating claim intake, AI assessment, and persistence.
    """
    @staticmethod
    def generate_claim_id() -> str:
        timestamp_part = int(time.time())
        random_suffix = random.randint(100, 999)
        return f"CR{timestamp_part}{random_suffix}"

    @classmethod
    def process_new_claim(cls, db: Session, request: SubmitClaimRequest) -> Dict[str, Any]:
        claim_id = cls.generate_claim_id()

        # 1. Create initial claim record
        claim = Claim(
            claim_id=claim_id,
            farmer_id=request.farmerId.strip(),
            crop_type=request.cropType.lower().strip(),
            claimed_damage=float(request.claimedDamage),
            status="EVALUATING"
        )
        claim = claim_repository.create_claim(db, claim)

        # 2. Record initial submission in audit log
        submission_log = AuditLog(
            claim_id=claim_id,
            event_type="CLAIM_SUBMITTED",
            actor="FARMER",
            details=json.dumps({
                "farmerId": request.farmerId,
                "cropType": request.cropType,
                "claimedDamage": request.claimedDamage
            })
        )
        claim_repository.create_audit_log(db, submission_log)

        # 3. Execute vision assessment via ML provider on all uploaded photos
        images = request.get_image_list()
        assessment_result = ml_provider.assess_crop_images(images, claim_id)

        # 4. Save assessment record
        assessment = ClaimAssessment(
            claim_id=claim_id,
            visual_class=assessment_result["visualClass"],
            damage_severity=assessment_result["damageSeverity"],
            confidence=assessment_result["confidence"]
        )
        claim_repository.save_assessment(db, assessment)

        # 5. Update claim with primary image path and ASSESSED status
        primary_image_path = assessment_result.get("imagePath")
        claim = claim_repository.update_claim_status(
            db,
            claim_id=claim_id,
            status="ASSESSED",
            image_path=primary_image_path
        )

        # 6. Record assessment completion in audit log
        assessment_log = AuditLog(
            claim_id=claim_id,
            event_type="VISION_ASSESSED",
            actor="SYSTEM",
            details=json.dumps({
                "visualClass": assessment_result["visualClass"],
                "damageSeverity": assessment_result["damageSeverity"],
                "confidence": assessment_result["confidence"],
                "imageCount": assessment_result.get("imageCount", 1),
                "imagePaths": assessment_result.get("imagePaths", []),
                "rawProbability": assessment_result.get("rawProbability")
            })
        )
        claim_repository.create_audit_log(db, assessment_log)

        # 7. Return complete claim response
        return {
            "claimId": claim.claim_id,
            "farmerId": claim.farmer_id,
            "cropType": claim.crop_type,
            "claimedDamage": claim.claimed_damage,
            "imagePath": claim.image_path,
            "status": claim.status,
            "visualAssessment": {
                "visualClass": assessment.visual_class,
                "damageSeverity": assessment.damage_severity,
                "confidence": assessment.confidence,
                "imageCount": assessment_result.get("imageCount", 1),
                "imagePaths": assessment_result.get("imagePaths", []),
                "imageAssessments": assessment_result.get("imageAssessments"),
                "rawProbability": assessment_result.get("rawProbability"),
                "imagePath": claim.image_path
            },
            "createdAt": claim.created_at.isoformat() if claim.created_at else None
        }

    @staticmethod
    def get_claim_details(db: Session, claim_id: str) -> Dict[str, Any]:
        claim = claim_repository.get_claim_by_id(db, claim_id)
        if not claim:
            raise AppError(
                message=f"Claim with ID '{claim_id}' was not found.",
                status_code=404,
                error_code=error_codes.CLAIM_NOT_FOUND
            )

        latest_assessment = claim_repository.get_latest_assessment(db, claim_id)
        assessment_data = latest_assessment.to_dict() if latest_assessment else None

        claim_data = claim.to_dict()
        claim_data["visualAssessment"] = assessment_data
        claim_data["auditLogs"] = [log.to_dict() for log in claim.audit_logs]
        return claim_data

    @staticmethod
    def list_all_claims(db: Session, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        claims = claim_repository.list_claims(db, skip=skip, limit=limit)
        results = []
        for claim in claims:
            latest_assessment = claim_repository.get_latest_assessment(db, claim.claim_id)
            claim_dict = claim.to_dict()
            claim_dict["visualAssessment"] = latest_assessment.to_dict() if latest_assessment else None
            results.append(claim_dict)
        return results

claim_service = ClaimService()
