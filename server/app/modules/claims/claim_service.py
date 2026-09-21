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
from app.providers.satellite_provider import satellite_provider, SatelliteProvider
from app.core.weather_engine import weather_engine
from app.core.satellite_engine import satellite_engine
from app.core.multimodal_engine import multimodal_engine
from app.core.image_hash import image_hasher
from app.core.fraud_engine import fraud_engine
from app.core.claim_decision_engine import claim_decision_engine
from app.core.xai_engine import xai_engine
from app.errors.app_error import AppError
import app.errors.error_codes as error_codes

# Configurable policy flag: Set to True to allow duplicate/recycled crop photos without fraud penalties
ALLOW_DUPLICATE_IMAGES: bool = True

class ClaimService:
    """
    Business service orchestrating claim intake, multimodal AI assessment,
    perceptual image hashing, fraud detection, and persistence.
    """
    @staticmethod
    def generate_claim_id() -> str:
        timestamp_part = int(time.time())
        random_suffix = random.randint(100, 999)
        return f"CR{timestamp_part}{random_suffix}"

    @classmethod
    def process_new_claim(cls, db: Session, request: SubmitClaimRequest) -> Dict[str, Any]:
        claim_id = cls.generate_claim_id()

        # Calculate representative latitude and longitude if polygon is provided
        calc_lat = request.latitude
        calc_lon = request.longitude
        if (calc_lat is None or calc_lon is None) and request.fieldBoundary and len(request.fieldBoundary) >= 3:
            calc_lat, calc_lon = SatelliteProvider.calculate_centroid(request.fieldBoundary)

        # 1. Create initial claim record with location, field boundary, and disaster date
        field_boundary_str = json.dumps(request.fieldBoundary) if request.fieldBoundary else None
        claim = Claim(
            claim_id=claim_id,
            farmer_id=request.farmerId.strip(),
            crop_type=request.cropType.lower().strip(),
            claimed_damage=float(request.claimedDamage),
            latitude=calc_lat,
            longitude=calc_lon,
            incident_date=request.incidentDate,
            field_boundary=field_boundary_str,
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
                "latitude": calc_lat,
                "longitude": calc_lon,
                "incidentDate": request.incidentDate,
                "hasFieldBoundary": bool(request.fieldBoundary)
            })
        )
        claim_repository.create_audit_log(db, submission_log)

        # 3. Stage 1: Execute vision assessment via ML provider on all uploaded photos
        images = request.get_image_list()
        assessment_result = ml_provider.assess_crop_images(images, claim_id)

        # Determine whether duplicate images are allowed (request override or system default)
        allow_duplicates = (
            request.allowDuplicateImages
            if request.allowDuplicateImages is not None
            else ALLOW_DUPLICATE_IMAGES
        )

        # Compute perceptual image hash of the primary photo to check for duplicate recycled images
        primary_image_hash = image_hasher.compute_dhash(images[0])
        duplicate_match = claim_repository.find_duplicate_image(
            db=db,
            target_hash=primary_image_hash,
            exclude_claim_id=claim_id
        )
        is_duplicate = bool(duplicate_match is not None)

        # Query past claims frequency for this farmer in the last 12 months
        farmer_claim_count = claim_repository.count_farmer_claims_12m(db, request.farmerId.strip())
        if request.claimFrequency is not None:
            farmer_claim_count = max(farmer_claim_count, request.claimFrequency)

        # 4. Stage 2: Execute weather evaluation & cause classification if location available
        weather_assessment = None
        damage_cause = "NORMAL" if assessment_result["visualClass"] == "HEALTHY" else "DAMAGED"
        incident_dt = request.incidentDate or datetime.utcnow().strftime("%Y-%m-%d")

        if calc_lat is not None and calc_lon is not None:
            raw_weather = weather_provider.get_weather_data(
                latitude=calc_lat,
                longitude=calc_lon,
                incident_date=incident_dt
            )
            # Incorporate client scenario / simulation overrides if supplied
            if request.rainfall is not None:
                raw_weather["rainfall_mm"] = float(request.rainfall)
            if request.temperature is not None:
                raw_weather["temp_max"] = float(request.temperature)
            if request.droughtIndex is not None:
                raw_weather["spei_drought_index"] = float(request.droughtIndex)

            weather_assessment = weather_engine.evaluate_weather(weather_data=raw_weather)
            fusion_result = multimodal_engine.fuse_assessments(
                visual_damage=assessment_result["damageSeverity"],
                weather_assessment=weather_assessment
            )
            damage_cause = fusion_result["damageCause"]
            weather_assessment["damageCause"] = damage_cause
            weather_assessment["consistencyNote"] = fusion_result.get("consistencyNote")

        # 5. Stage 3: Execute satellite remote sensing if field boundary polygon is provided
        satellite_assessment = None
        if request.fieldBoundary and len(request.fieldBoundary) >= 3:
            raw_satellite = satellite_provider.get_satellite_data(
                field_boundary=request.fieldBoundary,
                incident_date=incident_dt
            )
            satellite_assessment = satellite_engine.evaluate_field(
                field_boundary=request.fieldBoundary,
                satellite_data=raw_satellite
            )

        # 6. Stage 4: Execute Multimodal AI Fusion and Fraud Detection Engine (XGBoost)
        fraud_result = fraud_engine.evaluate(
            claimed_damage=claim.claimed_damage,
            visual_damage=assessment_result["damageSeverity"],
            weather_score=weather_assessment["weatherScore"] if weather_assessment else None,
            weather_hazard=weather_assessment.get("weatherHazard") if weather_assessment else None,
            satellite_damaged_area=satellite_assessment["damagedAreaPercentage"] if satellite_assessment else None,
            ndvi_vegetation_drop=satellite_assessment["ndviDrop"] if satellite_assessment else None,
            is_duplicate_image=is_duplicate,
            claims_frequency_12m=farmer_claim_count,
            allow_duplicate_images=allow_duplicates
        )

        # 7. Save assessment record combining all 4 stages of evidence
        assessment = ClaimAssessment(
            claim_id=claim_id,
            visual_class=assessment_result["visualClass"],
            damage_severity=assessment_result["damageSeverity"],
            confidence=assessment_result["confidence"],
            weather_score=weather_assessment["weatherScore"] if weather_assessment else None,
            damage_cause=damage_cause,
            weather_details=json.dumps(weather_assessment) if weather_assessment else None,
            satellite_score=satellite_assessment["satelliteScore"] if satellite_assessment else None,
            damaged_area_percentage=satellite_assessment["damagedAreaPercentage"] if satellite_assessment else None,
            satellite_details=json.dumps(satellite_assessment) if satellite_assessment else None,
            fraud_risk_score=fraud_result["fraudRiskScore"],
            fraud_risk_level=fraud_result["fraudRiskLevel"],
            decision=fraud_result["decision"],
            recommended_payout=fraud_result["recommendedPayout"],
            fraud_flags=json.dumps(fraud_result["fraudFlags"])
        )
        claim_repository.save_assessment(db, assessment)

        # 8. Update claim status to automated decision and save primary image path and hash
        primary_image_path = assessment_result.get("imagePath")
        claim = claim_repository.update_claim_status(
            db,
            claim_id=claim_id,
            status=fraud_result["decision"],
            image_path=primary_image_path,
            image_hash=primary_image_hash
        )

        # 9. Record audit logs for each pipeline stage
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
                "rawProbability": assessment_result.get("rawProbability"),
                "imageHash": primary_image_hash
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

        if satellite_assessment:
            satellite_log = AuditLog(
                claim_id=claim_id,
                event_type="SATELLITE_VERIFIED",
                actor="SYSTEM",
                details=json.dumps({
                    "preDisasterNdvi": satellite_assessment["preDisasterNdvi"],
                    "postDisasterNdvi": satellite_assessment["postDisasterNdvi"],
                    "ndviDrop": satellite_assessment["ndviDrop"],
                    "damagedAreaPercentage": satellite_assessment["damagedAreaPercentage"],
                    "satelliteScore": satellite_assessment["satelliteScore"],
                    "damageClassification": satellite_assessment["damageClassification"],
                    "fieldAreaHectares": satellite_assessment["fieldAreaHectares"],
                    "dataSource": satellite_assessment["dataSource"]
                })
            )
            claim_repository.create_audit_log(db, satellite_log)

        fraud_log = AuditLog(
            claim_id=claim_id,
            event_type="FRAUD_EVALUATED",
            actor="SYSTEM",
            details=json.dumps({
                "fraudRiskScore": fraud_result["fraudRiskScore"],
                "fraudRiskLevel": fraud_result["fraudRiskLevel"],
                "fraudFlags": fraud_result["fraudFlags"],
                "isDuplicateImage": is_duplicate,
                "allowDuplicateImages": allow_duplicates,
                "duplicateMatchedClaimId": duplicate_match.claim_id if duplicate_match else None
            })
        )
        claim_repository.create_audit_log(db, fraud_log)

        decision_log = AuditLog(
            claim_id=claim_id,
            event_type="DECISION_ISSUED",
            actor="SYSTEM",
            details=json.dumps({
                "decision": fraud_result["decision"],
                "recommendedPayout": fraud_result["recommendedPayout"],
                "claimedDamage": claim.claimed_damage,
                "verifiedGroundTruthDamage": fraud_result["verifiedGroundTruthDamage"]
            })
        )
        claim_repository.create_audit_log(db, decision_log)

        # 10. Stage 5: Generate Explainable AI (Tree SHAP) factor breakdown
        xai_result = xai_engine.explain_claim(
            feature_vector=fraud_result["featureVector"],
            decision=fraud_result["decision"]
        )

        xai_log = AuditLog(
            claim_id=claim_id,
            event_type="EXPLAINABILITY_GENERATED",
            actor="SYSTEM",
            details=json.dumps({
                "topDrivers": [d["label"] for d in xai_result["topDrivers"]],
                "executiveSummary": xai_result["executiveSummary"]
            })
        )
        claim_repository.create_audit_log(db, xai_log)

        # 11. Return complete multimodal claim response
        weather_score_val = weather_assessment["weatherScore"] if weather_assessment else None
        sat_area_val = satellite_assessment["damagedAreaPercentage"] if satellite_assessment else None
        weather_consistency_val = round(sat_area_val if sat_area_val is not None else (weather_score_val if weather_score_val is not None else 80.0), 2)
        field_area_ha = request.fieldAreaHectares or (satellite_assessment.get("fieldAreaHectares") if satellite_assessment else None)

        return {
            "claimId": claim.claim_id,
            "farmerId": claim.farmer_id,
            "cropType": claim.crop_type,
            "claimedDamage": claim.claimed_damage,
            "latitude": claim.latitude,
            "longitude": claim.longitude,
            "incidentDate": claim.incident_date,
            "lossDate": claim.incident_date,
            "fieldId": request.fieldId,
            "fieldAreaHectares": field_area_ha,
            "fieldBoundary": request.fieldBoundary,
            "imagePath": claim.image_path,
            "imageHash": primary_image_hash,
            "isDuplicateImage": is_duplicate,
            "allowDuplicateImages": allow_duplicates,
            "status": claim.status,
            "decision": fraud_result["decision"],
            "damageCause": damage_cause,
            "fraudRiskScore": fraud_result["fraudRiskScore"],
            "fraudScore": fraud_result["fraudRiskScore"],
            "fraudRiskLevel": fraud_result["fraudRiskLevel"],
            "riskLevel": fraud_result["fraudRiskLevel"],
            "recommendedPayout": fraud_result["recommendedPayout"],
            "payoutPercentage": fraud_result["recommendedPayout"],
            "damageScore": assessment.damage_severity,
            "damageSeverity": assessment.damage_severity,
            "confidence": assessment.confidence,
            "predictedClass": assessment.visual_class,
            "visualClass": assessment.visual_class,
            "weatherConsistency": weather_consistency_val,
            "fraudFlags": fraud_result["fraudFlags"],
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
            "assessment": {
                "decision": fraud_result["decision"],
                "damageScore": assessment.damage_severity,
                "damageSeverity": assessment.damage_severity,
                "confidence": assessment.confidence,
                "predictedClass": assessment.visual_class,
                "visualClass": assessment.visual_class,
                "fraudScore": fraud_result["fraudRiskScore"],
                "fraudRiskScore": fraud_result["fraudRiskScore"],
                "riskLevel": fraud_result["fraudRiskLevel"],
                "fraudRiskLevel": fraud_result["fraudRiskLevel"],
                "recommendedPayout": fraud_result["recommendedPayout"],
                "payoutPercentage": fraud_result["recommendedPayout"],
                "weatherConsistency": weather_consistency_val,
            },
            "weatherAssessment": weather_assessment,
            "satelliteAssessment": satellite_assessment,
            "fraudAssessment": fraud_result,
            "explainableAi": xai_result,
            "createdAt": claim.created_at.isoformat() if claim.created_at else None,
            "updatedAt": claim.updated_at.isoformat() if claim.updated_at else None
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
        claim_data["lossDate"] = claim.incident_date
        claim_data["visualAssessment"] = assessment_data
        claim_data["assessment"] = assessment_data
        claim_data["weatherAssessment"] = assessment_data.get("weatherDetails") if assessment_data else None
        claim_data["satelliteAssessment"] = assessment_data.get("satelliteDetails") if assessment_data else None
        claim_data["decision"] = assessment_data.get("decision") if assessment_data else claim.status
        claim_data["fraudRiskScore"] = assessment_data.get("fraudRiskScore") if assessment_data else None
        claim_data["fraudScore"] = assessment_data.get("fraudRiskScore") if assessment_data else None
        claim_data["fraudRiskLevel"] = assessment_data.get("fraudRiskLevel") if assessment_data else None
        claim_data["riskLevel"] = assessment_data.get("fraudRiskLevel") if assessment_data else None
        claim_data["recommendedPayout"] = assessment_data.get("recommendedPayout") if assessment_data else None
        claim_data["payoutPercentage"] = assessment_data.get("recommendedPayout") if assessment_data else None
        claim_data["damageScore"] = assessment_data.get("damageSeverity") if assessment_data else None
        claim_data["damageSeverity"] = assessment_data.get("damageSeverity") if assessment_data else None
        claim_data["confidence"] = assessment_data.get("confidence") if assessment_data else None
        claim_data["predictedClass"] = assessment_data.get("visualClass") if assessment_data else None
        claim_data["visualClass"] = assessment_data.get("visualClass") if assessment_data else None
        claim_data["weatherConsistency"] = (assessment_data.get("damagedAreaPercentage") or assessment_data.get("weatherScore")) if assessment_data else None
        claim_data["fraudFlags"] = assessment_data.get("fraudFlags") if assessment_data else []
        
        # Compute on-demand SHAP explanations for claim details view
        if latest_assessment:
            try:
                feat_dict = {
                    "claimed_damage": claim.claimed_damage,
                    "visual_damage_severity": latest_assessment.damage_severity,
                    "weather_score": latest_assessment.weather_score or 50.0,
                    "weather_hazard_match": 1 if latest_assessment.damage_cause in ["FLOOD", "DROUGHT", "STORM_LODGING"] else 0,
                    "satellite_damaged_area": latest_assessment.damaged_area_percentage or claim.claimed_damage,
                    "ndvi_vegetation_drop": 0.35 if (latest_assessment.damaged_area_percentage or 0) > 50 else 0.15,
                    "visual_vs_claim_gap": round(claim.claimed_damage - latest_assessment.damage_severity, 2),
                    "satellite_vs_claim_gap": round(claim.claimed_damage - (latest_assessment.damaged_area_percentage or claim.claimed_damage), 2),
                    "is_duplicate_image": 1 if latest_assessment.fraud_risk_score and latest_assessment.fraud_risk_score >= 0.95 else 0,
                    "claims_frequency_12m": 1
                }
                claim_data["explainableAi"] = xai_engine.explain_claim(feat_dict, decision=latest_assessment.decision)
            except Exception:
                claim_data["explainableAi"] = None
        else:
            claim_data["explainableAi"] = None

        claim_data["auditLogs"] = [log.to_dict() for log in claim.audit_logs]
        return claim_data

    @staticmethod
    def list_all_claims(db: Session, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        claims = claim_repository.list_claims(db, skip=skip, limit=limit)
        results = []
        for claim in claims:
            latest_assessment = claim_repository.get_latest_assessment(db, claim.claim_id)
            claim_dict = claim.to_dict()
            claim_dict["lossDate"] = claim.incident_date
            claim_dict["visualAssessment"] = latest_assessment.to_dict() if latest_assessment else None
            claim_dict["assessment"] = latest_assessment.to_dict() if latest_assessment else None
            if latest_assessment:
                claim_dict["decision"] = latest_assessment.decision
                claim_dict["fraudRiskScore"] = latest_assessment.fraud_risk_score
                claim_dict["fraudScore"] = latest_assessment.fraud_risk_score
                claim_dict["fraudRiskLevel"] = latest_assessment.fraud_risk_level
                claim_dict["riskLevel"] = latest_assessment.fraud_risk_level
                claim_dict["recommendedPayout"] = latest_assessment.recommended_payout
                claim_dict["payoutPercentage"] = latest_assessment.recommended_payout
                claim_dict["damageScore"] = latest_assessment.damage_severity
                claim_dict["damageSeverity"] = latest_assessment.damage_severity
                claim_dict["confidence"] = latest_assessment.confidence
                claim_dict["predictedClass"] = latest_assessment.visual_class
                claim_dict["visualClass"] = latest_assessment.visual_class
                claim_dict["weatherConsistency"] = latest_assessment.damaged_area_percentage or latest_assessment.weather_score
            results.append(claim_dict)
        return results

    @staticmethod
    def clear_all_claims(db: Session) -> int:
        count = db.query(Claim).count()
        db.query(AuditLog).delete()
        db.query(ClaimAssessment).delete()
        db.query(Claim).delete()
        db.commit()
        return count

claim_service = ClaimService()
