import json
import time
import random
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from datetime import datetime
from app.db.models import Claim, ClaimAssessment, AuditLog
from app.modules.claims.claim_repository import claim_repository
from app.modules.claims.claim_schema import SubmitClaimRequest
from app.providers.ml_provider import ml_provider
from app.providers.weather_provider import weather_provider
from app.core.weather_engine import weather_engine
from app.core.multimodal_engine import multimodal_engine
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

        # 1. Create initial claim record with location and disaster date
        claim = Claim(
            claim_id=claim_id,
            farmer_id=request.farmerId.strip(),
            crop_type=request.cropType.lower().strip(),
            claimed_damage=float(request.claimedDamage),
            latitude=request.latitude,
            longitude=request.longitude,
            incident_date=request.incidentDate,
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
                "claimedDamage": request.claimedDamage,
                "latitude": request.latitude,
                "longitude": request.longitude,
                "incidentDate": request.incidentDate
            })
        )
        claim_repository.create_audit_log(db, submission_log)

        # 3. Execute vision assessment via ML provider on all uploaded photos
        images = request.get_image_list()
        assessment_result = ml_provider.assess_crop_images(images, claim_id)

        # 4. Execute weather evaluation & multimodal fusion if location provided
        weather_assessment = None
        damage_cause = "NORMAL" if assessment_result["visualClass"] == "HEALTHY" else "DAMAGED"

        if request.latitude is not None and request.longitude is not None:
            incident_dt = request.incidentDate or datetime.utcnow().strftime("%Y-%m-%d")
            raw_weather = weather_provider.get_weather_data(
                latitude=request.latitude,
                longitude=request.longitude,
                incident_date=incident_dt
            )
            weather_assessment = weather_engine.evaluate_weather(weather_data=raw_weather)
            fusion_result = multimodal_engine.fuse_assessments(
                visual_damage=assessment_result["damageSeverity"],
                weather_assessment=weather_assessment
            )
            damage_cause = fusion_result["damageCause"]
            weather_assessment["damageCause"] = damage_cause
            weather_assessment["consistencyNote"] = fusion_result.get("consistencyNote")

        # 5. Save assessment record (combining visual + weather metrics)
        assessment = ClaimAssessment(
            claim_id=claim_id,
            visual_class=assessment_result["visualClass"],
            damage_severity=assessment_result["damageSeverity"],
            confidence=assessment_result["confidence"],
            weather_score=weather_assessment["weatherScore"] if weather_assessment else None,
            damage_cause=damage_cause,
            weather_details=json.dumps(weather_assessment) if weather_assessment else None
        )
        claim_repository.save_assessment(db, assessment)

        # 6. Update claim with primary image path and ASSESSED status
        primary_image_path = assessment_result.get("imagePath")
        claim = claim_repository.update_claim_status(
            db,
            claim_id=claim_id,
            status="ASSESSED",
            image_path=primary_image_path
        )

        # 7. Record assessment completion in audit log
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

        if weather_assessment:
            weather_log = AuditLog(
                claim_id=claim_id,
                event_type="WEATHER_VERIFIED",
                actor="SYSTEM",
                details=json.dumps({
                    "weatherScore": weather_assessment["weatherScore"],
                    "damageCause": damage_cause,
                    "anomalyDetected": weather_assessment["anomalyDetected"],
                    "dataSource": weather_assessment.get("dataSource")
                })
            )
            claim_repository.create_audit_log(db, weather_log)

        # 8. Return complete multimodal claim response
        return {
            "claimId": claim.claim_id,
            "farmerId": claim.farmer_id,
            "cropType": claim.crop_type,
            "claimedDamage": claim.claimed_damage,
            "latitude": claim.latitude,
            "longitude": claim.longitude,
            "incidentDate": claim.incident_date,
            "imagePath": claim.image_path,
            "status": claim.status,
            "damageCause": damage_cause,
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
            "weatherAssessment": weather_assessment,
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
